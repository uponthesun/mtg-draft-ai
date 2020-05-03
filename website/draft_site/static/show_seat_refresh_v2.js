function format_display() {
    html = `<i>Last updated: ${new Date().toTimeString()}</i><br>`
    return html;
}

async function checkWaitingForDrafters() {
    const url = location + '/is-pack-available';

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.available) {
            location.reload()
        } else {
            document.getElementById('waiting-for-drafters').innerHTML = format_display()
        }
    } catch (e) {
        console.error(e)
    }

    setTimeout(() => checkWaitingForDrafters(), 5000);
}

checkWaitingForDrafters()
