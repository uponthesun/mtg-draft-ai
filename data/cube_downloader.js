// ==UserScript==
// @name         cube_tutor_tag_downloader
// @version      0.1
// @description  Downloads cards and associated tag data for a cube from Cube Tutor.
// @author       Matthew McKay
// @match        http://www.cubetutor.com/editcube/*
// @grant        none
// ==/UserScript==

'use strict';

// This is the last element of the search filter section of the UI, so the download
// button is added right after it so it is in a convenient place.
var SEARCH_FILTER_ELEMENT_ID = 'accordion_0'
var PAGE_LIST_ELEMENT_ID = 't-data-grid-pager'

// Ids for the generated downloaded button and its container.
var BUTTON_ID = 'download-card-tags';
var BUTTON_CONTAINER_ID = 'download-card-tags-button-container';

// The regular expression for pulling the cube id out of the URL. This finds the first number in
// in the URL preceded by a '/' and matches all of it, enforcing that we either see a non-numeral
// or the end of the string after.
var CUBE_ID_REGEX = /.*\/([0-9]*)[^0-9]*.*$/;

/**
 * The main function of this script, which gets run on execution.
 * Appends a button to the menu that will parse out and download the cube list into a file.
 */
(function() {
    var buttonNode = document.createElement('div');
    buttonNode.innerHTML = '<button id="' + BUTTON_ID + '" type="button">Download Card Tags</button>';
    buttonNode.setAttribute ('id', BUTTON_CONTAINER_ID);

    document.getElementById(SEARCH_FILTER_ELEMENT_ID).appendChild(buttonNode);

    // Calls out to downloadCardInfo() when the added button is clicked.
    document.getElementById(BUTTON_ID).addEventListener( 'click', downloadCardInfo, false);
})();

/**
 * A starter method for downloadCardPage(). This pulls out the number of pages from the page selector
 * element and uses regular expressions to get the cube id number from the URL. It then calls a method
 * that recursively downloads every page's data.
 */
function downloadCardInfo() {
    var tablePages = document.getElementsByClassName(PAGE_LIST_ELEMENT_ID)[0];
    var numPages = tablePages.childNodes.length;

    var url = window.location.href
    var cubeId = CUBE_ID_REGEX.exec(url)[1]; // The first matched group is at index 1.

    downloadCardPage('', 1, numPages, cubeId);
}

/**
 * Downloads a single page of card data from Cube Tutor. Using the arguments, constructs a URL to
 * request the given page from Cube Tutor then walks the HTML to read each card's row and
 * the properties in each column. This is done in a callback from the request to get the page data.
 *
 * After the data is retrieved, it gets added to the content and the next page is downloaded recursively,
 * until we reach numPages. At that point the current content is saved to a file.
 *
 * @param {string} content The generated output file content downloaded so far.
 * @param {number} page The page to download when running this function.
 * @param {number} numPages The total number of pages to download, so we know when to stop.
 * @param {string} cubeId The id of the current cube, for generating the URL to POST to.
 */
function downloadCardPage(content, page, numPages, cubeId) {
    // If we're on the last page, save the file with all the content that we have so far.
    if(page > numPages) {
        saveFile(content);
        // Otherwise, download the next page and process it.
    } else {
        // Download the specified page by performing a POST against a generated URL for the cube.
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
            // This function gets called multiple times, we only want to process the result in this case.
            if (this.readyState == 4 && this.status == 200) {
                var doc = generateDocumentFromString(this.responseText);
                content += downloadCardPageInfo(doc);
                downloadCardPage(content, page + 1, numPages, cubeId);
            }
        };
        xhttp.open('POST', 'http://www.cubetutor.com/editcube.grid.pager/' + page + '/grid?t:ac=' + cubeId, true);
        xhttp.send();
    }
}

function generateDocumentFromString(html) {
    var element = document.createElement('div');
    element.innerHTML = html;
    return element;
}

/**
 * Walks the HTML to read each card's row and the properties in each column, writing them
 * into a string in TOML format.
 *
 * @return {string} The content of all the cards for the current page.
 */
function downloadCardPageInfo(doc) {
    var tableBody = doc.getElementsByClassName('t-data-grid')[1].lastChild;
    var tableRows = tableBody.childNodes;

    var content = '';
    for(var i = 0; i < tableRows.length; i++) {
        var tableColumns = tableRows[i].childNodes;
        var cardName = tableColumns[1].firstChild.innerHTML.replace('"', '\"');
        var manaCost = parseManaCost(tableColumns[2].firstChild);
        var colorIdentity = parseColorIdentity(tableColumns[3].firstChild);
        var types = parseTypes(tableColumns[5].firstChild);
        var tags = parseTags(tableColumns[8]);
        // Note: This page does not have subtypes, so we can't use this for tribal information.

        content += '["' + cardName + '"]\n';
        content += 'mana_cost = ' + manaCost + '\n';
        content += 'color_identity = "' + colorIdentity + '"\n';
        content += 'types = ' + types + '\n';
        content += 'tags = ' + tags + '\n';
        content += '\n';
    }

    return content;
}

/**
 * Converts a DOM node containing a card's mana cost into an array of strings.
 *
 * @param {Element} symbolsElement The DOM element containing the card's mana cost.
 * @return {string[]} The array of mana symbols represented as strings.
 */
function parseManaCost(symbolsElement) {
    var symbolNodes = Array.from(symbolsElement.childNodes);
    var manaCost = symbolNodes.map(convertManaSymbol);
    return JSON.stringify(manaCost);
}

/**
 * Converts a DOM node containing a mana symbol into a string representing the symbol.
 *
 * @param {Element} symbolNode The DOM element containing a single mana symbol.
 * @return {string} The string representing the symbol.
 */
function convertManaSymbol(symbolNode) {
    var symbol = symbolNode.className;
    symbol = symbol.replace('symbol', '');
    return symbol;
}

/**
 * Converts a DOM node containing a color identity selector into the string
 * representing the selected color identity.
 *
 * @param {Element} colorElement The DOM element containing the card's color identity.
 * @return {string} The string representing the color identity of the card.
 */
function parseColorIdentity(colorElement) {
    var identity = getSelected(colorElement).text;
    // Change colorless to 'C' for consistency
    identity = identity.replace('Colourless', 'C');
    // Cut to the first word to remove unnecessary information in parentheses.
    identity = identity.split(' ')[0];
    return identity;
}

/**
 * Converts a DOM node containing a type selector into an array of the types of the card.
 *
 * @param {Element} typeElement The DOM element containing the card's type.
 * @return {string[]} An array of strings containing the types of the card.
 */
function parseTypes(typeElement) {
    var types = getSelected(typeElement).value.split('_');
    types = types.map(t => t.toLowerCase());
    return JSON.stringify(types);
}

/**
 * Converts a DOM node containing tag information into an array of the tags of the card.
 *
 * @param {Element} tagsElement The DOM element containing the card's tags.
 * @return {string[]} An array of strings containing the tags of the card.
 */
function parseTags(tagsElement) {
    var tags = tagsElement.firstChild.getAttribute('data-tags');
    return tags == null ? '[]' : tags;

}

/**
 * Pulls out the selected DOM node from a selector node.
 *
 * @param {Element} selector A DOM selector element.
 * @return {Element} The selected node.
 */
function getSelected(selector) {
    return selector.options[selector.selectedIndex];
}

/**
 * Wraps the given string in double quotes.
 *
 * @param {string} str The string to quote.
 * @return {string} The quoted string.
 */
function quoteString(str) {
    return '"' + str + '"';
}

/**
 * Saves the given content as text to a TOML file.
 *
 * @param {string} content The content to save to a file.
 */
function saveFile(content) {
    var file = document.createElement('a');
    file.href = 'data:text,' + content;
    file.download = 'card_tag_data.toml';
    file.click();
}
