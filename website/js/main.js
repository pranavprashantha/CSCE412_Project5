// Fieldline Run Club — interactive features (all in the browser, no server)

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile menu
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // 2. Year in the footer
  var year = document.getElementById("year");
  if (year) {
    year.textContent = new Date().getFullYear();
  }

  // 3. Events: filter by run type
  var filterButtons = document.querySelectorAll(".filters button");
  var events = document.querySelectorAll(".event");
  var empty = document.querySelector(".empty");
  filterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var type = button.dataset.filter;
      var shown = 0;
      filterButtons.forEach(function (b) {
        b.classList.toggle("active", b === button);
      });
      events.forEach(function (event) {
        var match = type === "all" || event.dataset.type === type;
        event.classList.toggle("hidden", !match);
        if (match) {
          shown++;
        }
      });
      if (empty) {
        empty.style.display = shown === 0 ? "block" : "none";
      }
    });
  });

  // 4. Sign in: check the fields in the browser
  var form = document.getElementById("signin-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var valid = true;
      var checks = [
        { id: "email", test: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }, message: "Enter a valid email address." },
        { id: "password", test: function (v) { return v.length >= 8; }, message: "Password must be at least 8 characters." }
      ];
      checks.forEach(function (check) {
        var input = document.getElementById(check.id);
        var field = input.closest(".field");
        var error = field.querySelector(".error");
        if (check.test(input.value.trim())) {
          field.classList.remove("invalid");
          error.textContent = "";
        } else {
          field.classList.add("invalid");
          error.textContent = check.message;
          valid = false;
        }
      });
      var notice = document.getElementById("signin-notice");
      if (valid) {
        notice.textContent = "Looks good. This is a demo site, so there are no real accounts and nothing was sent.";
        notice.classList.add("show");
        form.reset();
      } else {
        notice.classList.remove("show");
      }
    });
  }
});
