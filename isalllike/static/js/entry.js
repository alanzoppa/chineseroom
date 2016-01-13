$(document).ready(function() {

$('.source-slider').each( function(index) {
        $(this).prev('span').html(this.value);
    })

});

$(document).on('change, mousemove', '.source-slider', function(e){
    $(e.currentTarget).prev('span').html(e.currentTarget.value);
});

$(document).on('change', '.source-slider', function(e){
    var sliders = $('.source-slider');
    var values = sliders.map( function(i) { return parseInt(this.value) });
    var total = Array.prototype.reduce.call(
            values, function(a,b){return a+b}, 0
            );
    sliders.each(
            function(){ $(this).attr('max', 100-total+parseInt(this.value)); }
            )
    $("#totals").html(total);
});
