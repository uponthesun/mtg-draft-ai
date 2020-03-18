function createHTML(numDrafters, numPacks, cardsPerPack) {
    console.log('bar')

    a = document.getElementsByTagName('a')
    allPicks = Array.from(a).filter(x => "popover" === x.rel).map(x => x.text)
    console.log(allPicks)

    // create 2D array that matches table displayed on tappedout
    picksTable = []
    for (var r = 0; r < numPacks * cardsPerPack; r++) {
        picksTable.push(allPicks.slice(r * numDrafters, (r+1) * numDrafters))
    }

    drafterPickAndPacks = []
    for (var seat = 0; seat < numDrafters; seat++) {
        pickAndPacks = []

        for (var pack = 0; pack < numPacks; pack++) {
            direction = (pack % 2 === 0) ? 1 : -1
            for (var pick = 0; pick < cardsPerPack; pick++) {
                r = pack * cardsPerPack + pick
                c = seat
                picked = picksTable[r][c]
                packContents = []

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

    html = `<style>
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

    for (var seat = 0; seat < numDrafters; seat++) {
        html += `Drafter ${seat}\n`
        for (var entry of drafterPickAndPacks[seat]) {
            html += `<div class="pack">`
            for (var card of entry.pack) {
                wasPicked = card === entry.pick
                html += imageURL(card, wasPicked) + `\n`
            }

            html += `</div>\n`
            //html += `<div>${entry.pick} [${entry.pack}]\n`
        }
    }
    return html
}

function imageURL(cardName, wasPicked) {
    cssClass = wasPicked ? 'card-image highlight' : 'card-image'
    return `<img src="https://api.scryfall.com/cards/named?format=image&exact=${encodeURI(cardName)}" class="${cssClass}" width="146" height="204" />`
}

createHTML(6, 3, 15)
