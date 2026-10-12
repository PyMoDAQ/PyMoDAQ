// Adds a button to show/hide the navigation sidebar of the Read the Docs theme.
// The choice is remembered between pages.
(function () {
    var KEY = "pymodaq-docs-sidebar-hidden";

    function stored() {
        try {
            return window.localStorage.getItem(KEY) === "1";
        } catch (e) {
            return false;
        }
    }

    function store(hidden) {
        try {
            window.localStorage.setItem(KEY, hidden ? "1" : "0");
        } catch (e) {
            // storage unavailable: the choice only lasts for this page
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "pmq-sidebar-toggle";

        function apply(hidden) {
            document.body.classList.toggle("pmq-sidebar-hidden", hidden);
            button.innerHTML = hidden ? "&#9776;" : "&laquo;";
            button.title = hidden ? "Show the navigation sidebar" : "Hide the navigation sidebar";
            button.setAttribute("aria-label", button.title);
            button.setAttribute("aria-expanded", hidden ? "false" : "true");
        }

        button.addEventListener("click", function () {
            var hidden = !document.body.classList.contains("pmq-sidebar-hidden");
            apply(hidden);
            store(hidden);
        });

        apply(stored());
        document.body.appendChild(button);
    });
})();
