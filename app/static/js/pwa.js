(() => {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch((error) => {
            console.warn("PWA service worker kaydedilemedi.", error);
        });
    });
})();
