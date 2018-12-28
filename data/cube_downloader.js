// ==UserScript==
// @name         cube_tutor_tag_downloader
// @version      0.1
// @description  Downloads cards and associated tag data for a cube from Cube Tutor.
// @author       Matthew McKay
// @match        http://www.cubetutor.com/editcube/*
// @grant        none
// ==/UserScript==

'use strict';

var BUTTON_ID = 'download-card-tags';
var BUTTON_CONTAINER_ID = 'download-card-tags-button-container';

/**
 * The main function of this script, which gets run on execution.
 * Appends a button to the menu that will parse out and download the cube list into a file.
 */
(function() {
    var buttonNode = document.createElement('div');
    buttonNode.innerHTML = '<button id="' + BUTTON_ID + '" type="button">Download Card Tags</button>';
    buttonNode.setAttribute ('id', BUTTON_CONTAINER_ID);

    document.getElementById('accordion_0').appendChild(buttonNode);

    // Calls out to downloadCardInfo() when the added button is clicked.
    document.getElementById(BUTTON_ID).addEventListener( 'click', downloadCardInfo, false);
})();

/**
 * A starter method for downloadCardInfoRecursive(). Note that this assumes that you are on
 * the first page of the cube.
 */
function downloadCardInfo() {
    downloadCardInfoRecursive('', 0);
}
/**
 * The primary method for downloading the card data from cube tutor, which gets executed upon
 * the button from the main method being clicked. Walks the HTML to read each card's row and
 * the properties in each column, loading each subsequent page and retrieving its contents as well.
 *
 * Since the individual pages are not separate page loads, we can click through them in Javascript
 * to load the next page's data, but we have to wait a second before processing the DOM elements
 * to give them time to update.
 */
function downloadCardInfoRecursive(content, page) {
    content += downloadCardPageInfo();
    page +=1;

    var tablePages = document.getElementsByClassName('t-data-grid-pager')[0];
    var numPages = tablePages.childNodes.length;

    // If we're on the last page, save the file with all the content that we have so far.
    if(page == numPages) {
        saveFile(content);
    // Otherwise, load the next page and wait a second before downloading it.
    } else {
        var pageNodes = tablePages.childNodes[page].click();
        // Wait a second before calling back to get the next page's data.
        setTimeout(function () {
            downloadCardInfoRecursive(content, page);
        }, 1000);
    }
}

/**
 * Walks the HTML to read each card's row and the properties in each column, writing them
 * into a string in TOML format.
 *
 * @return {string} The content of all the cards for the current page.
 */
function downloadCardPageInfo() {
    var tableBody = document.getElementById('editCubeGrid').lastChild;
    var tableRows = tableBody.childNodes;

    var content = '';
    for(var i = 0; i < tableRows.length; i++) {
        var tableColumns = tableRows[i].childNodes;
        var cardName = tableColumns[1].firstChild.innerHTML;
        var manaCost = parseManaCost(tableColumns[2].firstChild);
        var colorIdentity = parseColorIdentity(tableColumns[3].firstChild);
        var types = parseTypes(tableColumns[5].firstChild);
        var tags = parseTags(tableColumns[8]);
        // Note: This page does not have subtypes, so we can't use this for tribal information.

        content += '[' + cardName + ']\n';
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
 * @param {Element} symbolColumn The DOM element containing the card's mana cost.
 * @return {string[]} The array of mana symbols represented as strings.
 */
function parseManaCost(symbolColumn) {
    var symbolNodes = Array.from(symbolColumn.childNodes);
    var manaCost = symbolNodes.map(convertManaSymbol);
    return arrayToString(manaCost);
}

/**
 * Converts a DOM node containing a mana symbol into a string representing the symbol.
 *
 * @param {Element} symbolNode The DOM element containing a single mana symbol.
 * @return {string} The string representing the symbol.
 */
function convertManaSymbol(symbolNode) {
    var symbol = symbolNode.className;
    symbol = symbol.replace("symbol", "");
    return symbol;
}

/**
 * Converts a DOM node containing a color identity selector into the string
 * representing the selected color identity.
 *
 * @param {Element} colorColumn The DOM element containing the card's color identity.
 * @return {string} The string representing the color identity of the card.
 */
function parseColorIdentity(colorColumn) {
    var identity = getSelected(colorColumn).text;
    // Change colorless to 'C' for consistency
    identity = identity.replace('Colourless', 'C');
    // Cut to the first word to remove unnecessary information in parentheses.
    identity = identity.split(' ')[0];
    return identity;
}

/**
 * Converts a DOM node containing a type selector into an array of the types of the card.
 *
 * @param {Element} typeColumn The DOM element containing the card's type.
 * @return {string[]} An array of strings containing the types of the card.
 */
function parseTypes(typeColumn) {
    var types = getSelected(typeColumn).value.split('_');
    types = types.map(t => t.toLowerCase());
    return arrayToString(types);
}

/**
 * Converts a DOM node containing tag information into an array of the tags of the card.
 *
 * @param {Element} tagsColumn The DOM element containing the card's tags.
 * @return {string[]} An array of strings containing the tags of the card.
 */
function parseTags(tagsColumn) {
    var tags = tagsColumn.firstChild.getAttribute('data-tags');
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
 * Converts an array to a parseable printed string.
 *
 * @param {Array} array The array to stringify.
 * @return {string} The stringified array
 */
function arrayToString(array) {
    if(array.length == 0) {
        return '[]'
    }
    var result = '[' + quoteString(array[0]);
    for(var i = 1; i < array.length; i++) {
        result += ', ' + quoteString(array[i]);
    }
    result += ']';
    return result;
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
