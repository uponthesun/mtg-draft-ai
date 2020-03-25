// ==UserScript==
// @name         tappedout_draft_display
// @version      0.3.1
// @description  Adds a visual display of the draft to the tappedout.net draft display page.
// @author       Winter Dong
// @match        *://tappedout.net/mtg-draft-simulator/draft/*
// @run-at       document-end
// @grant        none

// @homepageURL  https://github.com/uponthesun/mtg-draft-ai
// @updateURL    https://github.com/uponthesun/mtg-draft-ai/raw/master/data_mining/tappedout_draft_display.user.js

// ==/UserScript==

function createDisplayDivHTML(drafters, numPacks, cardsPerPack) {
    const numDrafters = drafters.length
    const a = document.getElementsByTagName('a')
    const allPicks = Array.from(a).filter(x => "popover" === x.rel).map(x => x.text)

    // create 2D array that matches table displayed on tappedout
    const picksTable = []
    for (var r = 0; r < numPacks * cardsPerPack; r++) {
        picksTable.push(allPicks.slice(r * numDrafters, (r+1) * numDrafters))
    }

    const drafterPickAndPacks = []
    for (var seat = 0; seat < numDrafters; seat++) {
        const pickAndPacks = []

        for (var pack = 0; pack < numPacks; pack++) {
            const direction = (pack % 2 === 0) ? 1 : -1
            for (var pick = 0; pick < cardsPerPack; pick++) {
                r = pack * cardsPerPack + pick
                var c = seat
                const picked = picksTable[r][c]
                const packContents = []

                for (var i = 0; i < cardsPerPack - pick; i++) {
                    packContents.push(picksTable[r][c])
                    r++
                    c = (numDrafters + c + direction) % numDrafters
                }
                pickAndPacks.push({pick: picked, pack: packContents})
            }
        }

        drafterPickAndPacks.push(pickAndPacks)
    }

    var html = `<style>
    card-image {
        display: inline;
        margin: 1px;
    }
    .highlight {
        border-width: 10px;
        border-color: red;
        border-style: solid;
    }
    .pack {
        border-color: black;
        border-style: solid;
        padding: 5px;
    }
    </style>`

    for (seat = 0; seat < numDrafters; seat++) {
        const name = drafters[seat]
        html += `<b>Drafter ${seat+1}: <a href="https://tappedout.net/users/${name}/">${name}</a></b>\n`
        for (var entry of drafterPickAndPacks[seat]) {
            html += `<div class="pack">`
            for (var card of entry.pack) {
                const wasPicked = card === entry.pick
                html += imageURL(card, wasPicked) + `\n`
            }

            html += `</div>\n`
        }
    }
    return html
}

function imageURL(cardName, wasPicked) {
    const cssClass = wasPicked ? 'card-image highlight' : 'card-image'
    return `<img src="https://api.scryfall.com/cards/named?format=image&exact=${encodeURI(cardName)}" class="${cssClass}" width="146" height="204" />`
}

function getDrafters() {
    const options = Array.from(document.getElementById('id_mtgo-seat').options)
    const drafters = options.map(o => o.text)
            .filter(t => t.includes('Seat'))
            .map(t => t.match(/Seat \d+: (\w+)/)[1].trim())
    return drafters
}

const draftTableRows = document.getElementsByTagName("tr")
const draftTableLastRow = draftTableRows.item(draftTableRows.length - 1)
const packDataCap = draftTableLastRow.firstElementChild.textContent.match(/(\d+) - (\d+)/)
const numPacks = packDataCap[1]
const packSize = packDataCap[2]

const displayDiv = document.createElement('div')
displayDiv.setAttribute('id', 'draftImagesDisplayDiv')
displayDiv.setAttribute('class', 'hidden')
displayDiv.innerHTML = createDisplayDivHTML(getDrafters(), numPacks, packSize)

const showDisplayButton = document.createElement('button')
showDisplayButton.innerHTML = 'show/hide draft images'
showDisplayButton.setAttribute('onclick', "showOrHide('draftImagesDisplayDiv')")

const buttonScript = document.createElement('script')
const scriptSrc = `
function showOrHide(divID) {
    const item = document.getElementById(divID);
    if (item) {
        newState = (item.className === 'hidden') ? 'unhidden' : 'hidden'
        item.className = newState
    }
}`
buttonScript.appendChild(document.createTextNode(scriptSrc))

const parentNode = document.getElementsByClassName("container margin-top-18")[0]
parentNode.insertBefore(displayDiv, parentNode.firstChild)
parentNode.insertBefore(showDisplayButton, parentNode.firstChild)
parentNode.insertBefore(buttonScript, parentNode.firstChild)
