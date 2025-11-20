(function () {
    const widget = document.getElementById("videoHelpWidget");
    if (!widget) return;

    const launcher = widget.querySelector(".video-help__launcher");
    const closeBtn = widget.querySelector(".video-help__close");
    const tabs = Array.from(widget.querySelectorAll(".video-help__tab"));
    const videos = Array.from(widget.querySelectorAll(".video-help__video"));
    const storageKey = "videoHelpCollapsed";

    const setCollapsed = (collapsed) => {
        widget.classList.toggle("video-help--collapsed", collapsed);
        if (launcher) {
            launcher.setAttribute("aria-hidden", collapsed ? "false" : "true");
            launcher.tabIndex = collapsed ? 0 : -1;
        }
        if (closeBtn) {
            closeBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }
        try {
            window.localStorage.setItem(storageKey, String(collapsed));
        } catch (error) {
            // Silently ignore storage errors (private windows, etc.)
        }
    };

    const setActiveVideo = (name) => {
        tabs.forEach((tab) => {
            const isActive = tab.dataset.target === name;
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", String(isActive));
            tab.setAttribute("tabindex", isActive ? "0" : "-1");
        });

        videos.forEach((video) => {
            const isActive = video.dataset.name === name;
            video.classList.toggle("is-active", isActive);
            video.setAttribute("aria-hidden", String(!isActive));
        });
    };

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            setActiveVideo(tab.dataset.target);
        });
        tab.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setActiveVideo(tab.dataset.target);
            }
        });
    });

    launcher?.addEventListener("click", () => setCollapsed(false));
    closeBtn?.addEventListener("click", () => setCollapsed(true));

    // Initialize state
    const shouldCollapse = (() => {
        try {
            return window.localStorage.getItem(storageKey) === "true";
        } catch (error) {
            return true;
        }
    })();

    setCollapsed(shouldCollapse);
    if (tabs.length) {
        setActiveVideo(tabs[0].dataset.target);
    }
})();

