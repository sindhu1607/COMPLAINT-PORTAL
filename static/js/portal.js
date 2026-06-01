(function () {
    const root = document.documentElement;
    const savedTheme = localStorage.getItem("portal-theme");
    if (savedTheme) {
        root.setAttribute("data-theme", savedTheme);
    }

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            localStorage.setItem("portal-theme", next);
        });
    });

    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            document.body.classList.toggle("sidebar-open");
        });
    });

    const detailLayout = document.querySelector("[data-status-url]");
    if (detailLayout) {
        const badge = detailLayout.querySelector("[data-status-badge]");
        const statusUrl = detailLayout.getAttribute("data-status-url");

        const updateStatus = async () => {
            try {
                const response = await fetch(statusUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
                if (!response.ok) return;
                const data = await response.json();
                if (badge && data.status_display) {
                    badge.className = `status status-${data.status}`;
                    badge.textContent = data.status_display;
                }
            } catch (error) {
                console.debug("Status refresh skipped", error);
            }
        };

        window.setInterval(updateStatus, 15000);
    }

    if (window.portalCharts && window.Chart) {
        const categoryCanvas = document.getElementById("categoryChart");
        const monthlyCanvas = document.getElementById("monthlyChart");
        const palette = ["#246bfd", "#12805c", "#b7791f", "#c7353f", "#6941c6", "#0e9384", "#dd6b20", "#475467"];

        if (categoryCanvas) {
            new Chart(categoryCanvas, {
                type: "doughnut",
                data: {
                    labels: window.portalCharts.categoryLabels,
                    datasets: [{
                        data: window.portalCharts.categoryValues,
                        backgroundColor: palette
                    }]
                },
                options: {
                    plugins: { legend: { position: "bottom" } },
                    cutout: "62%"
                }
            });
        }

        if (monthlyCanvas) {
            new Chart(monthlyCanvas, {
                type: "bar",
                data: {
                    labels: window.portalCharts.monthlyLabels,
                    datasets: [{
                        label: "Complaints",
                        data: window.portalCharts.monthlyValues,
                        backgroundColor: "#246bfd",
                        borderRadius: 8
                    }]
                },
                options: {
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    if (window.feedbackCharts && window.Chart) {
        const ratingCanvas = document.getElementById("ratingChart");
        if (ratingCanvas) {
            new Chart(ratingCanvas, {
                type: "bar",
                data: {
                    labels: window.feedbackCharts.labels,
                    datasets: [{
                        label: "Responses",
                        data: window.feedbackCharts.values,
                        backgroundColor: "#12805c",
                        borderRadius: 8
                    }]
                },
                options: {
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }
})();
