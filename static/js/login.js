$("#tabs").tabs({
    hide: 'fade',
    show: 'fade'
  });
  
  $(".button").click(function(event) {
    var form = $(this).closest("form");
    var id = form.attr('id');
  
    //Delay post by 1800
    event.preventDefault();
    setTimeout(function() {
      form.submit();
    }, 1800);
  
    //Set correct message
    if (id == "loginForm") {
      $("#message").text("Welcome...");
    }
    if (id == "signupForm") {
      $("#message").text("Thanks for signing up!");
    } 
  
    //Nice animation
    $('.login').fadeOut(250);
    $('.success').fadeIn(1100);
    $('.overlay').addClass('overlay-success', 400);
  });