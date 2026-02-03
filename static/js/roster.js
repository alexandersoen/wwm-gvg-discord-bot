/**
 * Roster Management Logic
 */
const RosterManager = {
  // Helper to sync the visual state of a row based on an active input
  updateRowState: function(rowClass, activeInput) {
    const rowInputs = document.querySelectorAll('.' + rowClass);
    rowInputs.forEach(inp => {
      const btn = inp.nextElementSibling;
      if (inp !== activeInput) {
        // If the active input has a value > 0, disable all other buttons
        btn.disabled = (parseInt(activeInput.value) > 0);
      }
    });
  },

  cycleValue: function(btn, max) {
    const input = btn.previousElementSibling;
    let current = parseInt(input.value);

    console.log(input.value, max)

    // 1. Calculate next value
    let next = (current >= max) ? 0 : current + 1;
    input.value = next;

    // 2. Update UI
    btn.innerText = next === 0 ? "-" : next;
    btn.setAttribute('data-active', next > 0);

    // 3. Handle Row Exclusion
    const rowClass = input.classList[0];
    this.updateRowState(rowClass, input);

    // 4. Trigger HTMX
    htmx.trigger("#roster-form", "change");
  },

  resetRow: function(rowClass) {
    const rowInputs = document.querySelectorAll('.' + rowClass);
    rowInputs.forEach(inp => {
      const btn = inp.nextElementSibling;
      inp.value = 0;
      btn.innerText = "-";
      btn.setAttribute('data-active', false);
      btn.disabled = false;
    });
    htmx.trigger("#roster-form", "change");
  }
};
