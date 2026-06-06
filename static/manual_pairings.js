(function () {
  function refreshSelects(form) {
    const selects = form.querySelectorAll("select.player-select");
    const chosen = new Map();

    selects.forEach(function (select) {
      const val = select.value;
      if (val) {
        chosen.set(select, val);
      }
    });

    selects.forEach(function (select) {
      const myValue = select.value;
      Array.from(select.options).forEach(function (option) {
        if (!option.value) {
          option.hidden = false;
          option.disabled = false;
          return;
        }
        let taken = false;
        chosen.forEach(function (val, other) {
          if (other !== select && val === option.value) {
            taken = true;
          }
        });
        option.disabled = taken && option.value !== myValue;
      });
    });
  }

  function init() {
    const form = document.getElementById("manual-pairings-form");
    if (!form) {
      return;
    }
    form.addEventListener("change", function () {
      refreshSelects(form);
    });
    refreshSelects(form);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
