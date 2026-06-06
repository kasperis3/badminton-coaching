(function () {
  function digitsOnly(value) {
    return String(value).replace(/\D/g, "");
  }

  function bindScoreInput(input) {
    input.addEventListener("input", function () {
      const cleaned = digitsOnly(input.value);
      if (input.value !== cleaned) {
        input.value = cleaned;
      }
    });

    input.addEventListener("keydown", function (event) {
      const allowed = [
        "Backspace",
        "Delete",
        "Tab",
        "Escape",
        "Enter",
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "Home",
        "End",
      ];
      if (allowed.indexOf(event.key) !== -1) {
        return;
      }
      if (event.ctrlKey || event.metaKey) {
        return;
      }
      if (event.key.length === 1 && !/^\d$/.test(event.key)) {
        event.preventDefault();
      }
    });

    input.addEventListener("paste", function (event) {
      event.preventDefault();
      const text = (event.clipboardData || window.clipboardData).getData("text");
      input.value = digitsOnly(text);
    });
  }

  function init() {
    document.querySelectorAll(".score-input").forEach(bindScoreInput);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
