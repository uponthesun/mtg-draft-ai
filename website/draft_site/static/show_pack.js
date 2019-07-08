function unhide(clickedButton, divID) {
    var item = document.getElementById(divID);
    if (item) {
        if(item.className=='hidden'){
            item.className = 'unhidden' ;
            clickedButton.value = 'Hide Bot Ratings'
        }else{
            item.className = 'hidden';
            clickedButton.value = 'Show Bot Ratings'
        }
    }
}