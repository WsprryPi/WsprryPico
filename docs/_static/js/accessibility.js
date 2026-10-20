/* Pico adaptation of WsprryPi-Docs mobile keyboard support; MIT, Lee Bussy. */
document.addEventListener("DOMContentLoaded", () => {
    const search = document.querySelector(".wy-side-nav-search");
    if (search) {
        const labelVersion = () => {
            const select = search.querySelector(".version-switch select");
            if (!select) return false;
            select.setAttribute("aria-label", "Documentation version");
            return true;
        };
        if (!labelVersion()) {
            const observer = new MutationObserver(() => {
                if (labelVersion()) observer.disconnect();
            });
            observer.observe(search, {childList: true, subtree: true});
        }
    }
    const main = document.querySelector("[role='main']");
    if (main) {
        main.id = "main-content";
        main.tabIndex = -1;
        const skip = document.createElement("a");
        skip.href = "#main-content";
        skip.className = "skip-link";
        skip.textContent = "Skip to content";
        document.body.prepend(skip);
    }
    const toggle = document.querySelector(".wy-nav-top-toggle");
    const label = toggle && toggle.querySelector(".visually-hidden");
    if (!toggle || !label) return;
    const side = document.querySelector(".wy-nav-side");
    if (side) { side.id = "manual-navigation"; toggle.setAttribute("aria-controls", side.id); }
    const shifted = () => document.querySelector(".wy-nav-content-wrap.shift") !== null;
    const sync = () => {
        toggle.setAttribute("aria-expanded", String(shifted()));
        label.textContent = shifted() ? "Close navigation menu" : "Open navigation menu";
    };
    // The theme also closes the menu after same-page navigation links.
    const content = document.querySelector(".wy-nav-content-wrap");
    if (content) new MutationObserver(sync).observe(content, {attributes: true, attributeFilter: ["class"]});
    document.addEventListener("keydown", event => {
        if (event.key !== "Escape" || !shifted()) return;
        document.querySelectorAll("[data-toggle='wy-nav-shift'], [data-toggle='rst-versions']")
            .forEach(element => element.classList.remove("shift"));
        sync(); toggle.focus();
    });
    sync();
});
