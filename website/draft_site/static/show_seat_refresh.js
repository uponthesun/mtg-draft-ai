function format_display(drafters) {
    html = '';
    for (drafter of drafters) {
        html += `Seat ${drafter.seat} - ${drafter.name}<br>`
    }
    html += `<i>Last updated: ${new Date().toTimeString()}</i><br>`
    return html;
}

async function checkWaitingForDrafters() {
    const url = location + '/waiting-for-drafters';

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.drafters.length == 0) {
            location.reload()
        } else {
            document.getElementById('waiting-for-drafters').innerHTML = format_display(data.drafters)
        }
    } catch (e) {
        console.error(e)
    }

    setTimeout(() => checkWaitingForDrafters(), 5000);
}

checkWaitingForDrafters()
