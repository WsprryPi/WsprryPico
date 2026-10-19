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
    const oldToggle = document.querySelector(".wy-nav-top [data-toggle='wy-nav-top']");
    if (!oldToggle) return;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "wy-nav-top-toggle";
    toggle.setAttribute("data-toggle", "wy-nav-top");
    toggle.setAttribute("aria-label", "Open navigation menu");
    toggle.innerHTML = '<span class="fa fa-bars" aria-hidden="true"></span>';
    const icon = toggle.querySelector("i");
    if (icon) icon.setAttribute("aria-hidden", "true");
    oldToggle.replaceWith(toggle);
    const side = document.querySelector(".wy-nav-side");
    if (side) { side.id = "manual-navigation"; toggle.setAttribute("aria-controls", side.id); }
    const shifted = () => document.querySelector(".wy-nav-content-wrap.shift") !== null;
    const sync = () => {
        toggle.setAttribute("aria-expanded", String(shifted()));
        toggle.setAttribute("aria-label", shifted() ? "Close navigation menu" : "Open navigation menu");
    };
    // The theme binds its delegated toggle handler before DOMContentLoaded.
    toggle.addEventListener("click", () => setTimeout(sync, 0));
    document.addEventListener("keydown", event => {
        if (event.key !== "Escape" || !shifted()) return;
        document.querySelectorAll("[data-toggle='wy-nav-shift'], [data-toggle='rst-versions']")
            .forEach(element => element.classList.remove("shift"));
        sync(); toggle.focus();
    });
    sync();
});
