/**
 * charts.js
 * -----------
 * Thin wrappers around Chart.js so every dashboard/report page renders
 * charts with the same color palette and options instead of repeating
 * boilerplate configuration.
 */

const CHART_PALETTE = ["#E8A33D", "#16213A", "#3B7DDB", "#1F9D6B", "#D9483B", "#8E6FCE"];

function destroyChartIfExists(canvasId) {
    const existing = Chart.getChart(canvasId);
    if (existing) existing.destroy();
}

function renderBarChart(canvasId, labels, data, label = "Value") {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    destroyChartIfExists(canvasId);

    return new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{ label, data, backgroundColor: CHART_PALETTE[0], borderRadius: 6, maxBarThickness: 42 }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, grid: { color: "#EEF0F5" } }, x: { grid: { display: false } } },
        },
    });
}

function renderLineChart(canvasId, labels, data, label = "Value") {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    destroyChartIfExists(canvasId);

    return new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label, data,
                borderColor: CHART_PALETTE[0],
                backgroundColor: "rgba(232,163,61,0.15)",
                tension: 0.35,
                fill: true,
                pointRadius: 3,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, grid: { color: "#EEF0F5" } }, x: { grid: { display: false } } },
        },
    });
}

function renderDoughnutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    destroyChartIfExists(canvasId);

    return new Chart(ctx, {
        type: "doughnut",
        data: { labels, datasets: [{ data, backgroundColor: CHART_PALETTE, borderWidth: 0 }] },
        options: {
            responsive: true,
            cutout: "68%",
            plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
        },
    });
}

function renderHorizontalBarChart(canvasId, labels, data, label = "Value") {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    destroyChartIfExists(canvasId);

    return new Chart(ctx, {
        type: "bar",
        data: { labels, datasets: [{ label, data, backgroundColor: CHART_PALETTE[2], borderRadius: 6 }] },
        options: {
            indexAxis: "y",
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true, grid: { color: "#EEF0F5" } }, y: { grid: { display: false } } },
        },
    });
}
