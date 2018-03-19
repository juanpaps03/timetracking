function updateClock(){
    var now = moment(),
    second = now.seconds() * 6,
    minute = now.minutes() * 6 + second / 60,
    hour = ((now.hours() % 12) / 12) * 360 + 90 + minute / 12;

    $('#hour').css("transform", "rotate(" + hour + "deg)");
    $('#minute').css("transform", "rotate(" + minute + "deg)");
    $('#second').css("transform", "rotate(" + second + "deg)");
}

function updateTime() {
    var now = moment();
    $('.date').html(now.format('D MMMM YYYY '));
    $('.time').html(now.format('H:mm:ss'));
}

function timedUpdate () {
    updateClock();
    updateTime();
    setTimeout(timedUpdate, 1000);
}

$( document ).ready(function() {
    timedUpdate();
});
