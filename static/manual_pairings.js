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
        // Still show taken names so you can pick them to swap; mark visually via disabled=false
        option.disabled = false;
        option.dataset.taken = taken && option.value !== myValue ? "1" : "";
      });
    });
  }

  function swapOrAssign(form, select, previousValue) {
    const newVal = select.value;
    if (!newVal) {
      refreshSelects(form);
      return;
    }

    const selects = form.querySelectorAll("select.player-select");
    selects.forEach(function (other) {
      if (other !== select && other.value === newVal) {
        other.value = previousValue || "";
      }
    });
    refreshSelects(form);
  }

  function init() {
    const form = document.getElementById("manual-pairings-form");
    if (!form) {
      return;
    }

    form.querySelectorAll("select.player-select").forEach(function (select) {
      select.addEventListener("focus", function () {
        select.dataset.previousValue = select.value;
      });
      select.addEventListener("change", function () {
        const previous = select.dataset.previousValue || "";
        swapOrAssign(form, select, previous);
        select.dataset.previousValue = select.value;
      });
    });

    refreshSelects(form);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
