$(document).on('change, mousemove', '.source-slider', function(e){
    $(e.currentTarget).prev('span').html(e.currentTarget.value);
});


var foo = function(e){
    var sliders = $('.source-slider');
    var values = sliders.map( function(i) { return parseInt(this.value) });
    var total = Array.prototype.reduce.call(
            values, function(a,b){return a+b}, 0
            );
    sliders.each(
            function(){
                console.log('foo');
                console.log(100-total+parseInt(this.value));
                $(this).attr('max', 100-total+parseInt(this.value));
            }
            )
    if (total == 100) { 
        $('#submit-run').removeAttr('disabled');
    }
    else {
        $('#submit-run').attr('disabled', 'disabled');
    }
    $('#submit-run').val(
            '('+ total + ' / 100) Submit'
            )
}



$(document).on('change', '.source-slider',  foo);

$(document).ready(function() {

$('.source-slider').each( function(index) {
        $(this).prev('span').html(this.value);
    })

foo();

});
