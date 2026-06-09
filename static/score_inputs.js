(function () {
  function validateMatch(scoreA, scoreB, gameTo) {
    if (scoreA === 0 && scoreB === 0) {
      return "Scores cannot both be 0.";
    }
    var atCap = 0;
    if (scoreA === gameTo) {
      atCap += 1;
    }
    if (scoreB === gameTo) {
      atCap += 1;
    }
    if (atCap === 0) {
      return "One side must reach " + gameTo + " points to win.";
    }
    if (atCap === 2) {
      return "Both sides cannot have " + gameTo + " points.";
    }
    return null;
  }

  function digitsOnly(value) {
    return String(value).replace(/\D/g, "");
  }

  function parseScore(raw) {
    var text = digitsOnly(raw).trim();
    if (!text) {
      return null;
    }
    return parseInt(text, 10);
  }

  function clampField(input, gameTo) {
    var cleaned = digitsOnly(input.value);
    if (input.value !== cleaned) {
      input.value = cleaned;
    }
    if (cleaned === "") {
      return;
    }
    var value = parseInt(cleaned, 10);
    if (value > gameTo) {
      input.value = String(gameTo);
    }
  }

  function getMatchCard(input) {
    return input.closest("article.match-card");
  }

  function getMatchInputs(card) {
    return card.querySelectorAll(".score-input");
  }

  function updateMatchCard(card, gameTo) {
    var inputs = getMatchInputs(card);
    if (inputs.length !== 2) {
      return false;
    }
    var scoreA = parseScore(inputs[0].value);
    var scoreB = parseScore(inputs[1].value);
    var hint = card.querySelector(".score-match-hint");
    var message = "";

    if (scoreA === null || scoreB === null) {
      card.classList.remove("score-match-invalid");
      if (hint) {
        hint.textContent = "";
      }
      return false;
    }

    var err = validateMatch(scoreA, scoreB, gameTo);
    if (err) {
      card.classList.add("score-match-invalid");
      message = err;
    } else {
      card.classList.remove("score-match-invalid");
    }
    if (hint) {
      hint.textContent = message;
    }
    return err === null;
  }

  function allMatchesValid(gameTo) {
    var cards = document.querySelectorAll("article.match-card");
    if (cards.length === 0) {
      return false;
    }
    var allValid = true;
    cards.forEach(function (card) {
      if (!updateMatchCard(card, gameTo)) {
        allValid = false;
      }
    });
    return allValid;
  }

  function updateSaveButton(gameTo) {
    var btn = document.getElementById("save-scores-btn");
    if (!btn) {
      return;
    }
    btn.disabled = !allMatchesValid(gameTo);
  }

  function bindScoreInput(input, gameTo) {
    function onChange() {
      clampField(input, gameTo);
      var card = getMatchCard(input);
      if (card) {
        updateMatchCard(card, gameTo);
      }
      updateSaveButton(gameTo);
    }

    input.addEventListener("input", onChange);
    input.addEventListener("blur", onChange);

    input.addEventListener("keydown", function (event) {
      var allowed = [
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
      var text = (event.clipboardData || window.clipboardData).getData("text");
      input.value = digitsOnly(text);
      onChange();
    });
  }

  function init() {
    var form = document.getElementById("scores-form");
    if (!form) {
      return;
    }
    var gameTo = parseInt(form.getAttribute("data-game-to"), 10);
    if (!gameTo) {
      return;
    }

    document.querySelectorAll(".score-input").forEach(function (input) {
      bindScoreInput(input, gameTo);
    });

    form.addEventListener("submit", function (event) {
      if (!allMatchesValid(gameTo)) {
        event.preventDefault();
      }
    });

    updateSaveButton(gameTo);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
