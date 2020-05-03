function format_display(drafters) {
    let html = ''
    for (const drafter of drafters) {
        html += `Seat ${drafter.seat} - ${drafter.name}: ${drafter.queued_packs}<br>`
    }
    html += `<i>Last updated: ${new Date().toTimeString()}</i><br>`
    return html;
}

async function checkWaitingForDrafters() {
    //const url = location + '/is-pack-available';
    const url = location.origin + '/draft/214/queued-packs'

    try {
        const response = await fetch(url);
        const data = await response.json();

        const isWaiting = document.getElementById('waiting').value === "true"
        const currentSeat = parseInt(document.getElementById('current-seat').value);
        const numQueued = data.drafters.filter(d => d.seat == currentSeat)[0].queued_packs

        document.getElementById('queued-packs').innerHTML = format_display(data.drafters)

        if (numQueued > 0 && isWaiting) {
            //location.reload()
        }
    } catch (e) {
        console.error(e)
    }

    setTimeout(() => checkWaitingForDrafters(), 5000);
}

checkWaitingForDrafters()
