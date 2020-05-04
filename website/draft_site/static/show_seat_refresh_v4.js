function format_display(drafters) {
    let html = `<b>Queued Packs</b> - <i>Last updated: ${new Date().toTimeString()}</i><br>`

    human_drafters = drafters.filter(d => !d.is_bot)
    html += human_drafters.map(d => `${d.name}: ${d.queued_packs}`).join(', ')

    html += '<br>'
    return html;
}

async function checkWaitingForDrafters() {
    const draftId = document.getElementById('draft-id').value;
    const url = `${location.origin}/draft/${draftId}/queued-packs`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        const isWaiting = document.getElementById('waiting').value === "true"
        const currentSeat = parseInt(document.getElementById('current-seat').value);
        const numQueued = data.drafters.filter(d => d.seat == currentSeat)[0].queued_packs

        queued_packs_display = document.getElementById('queued-packs')
        if (queued_packs_display) {
            queued_packs_display.innerHTML = format_display(data.drafters);
        }

        if (numQueued > 0 && isWaiting) {
            location.reload()
        }
    } catch (e) {
        console.error(e)
    }

    setTimeout(() => checkWaitingForDrafters(), 5000);
}

checkWaitingForDrafters()
