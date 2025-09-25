document.addEventListener("DOMContentLoaded", () => {
    const restaurantId = window.RESTAURANT_ID;
    let donutChart, lineChart;

    // ======== Helper: tạo option cho tháng và quý =========
    function populateMonthQuarterSelects() {
        const now = new Date();
        const currentMonth = now.getMonth() + 1; // JS: 0-11 => +1
        const currentQuarter = Math.ceil(currentMonth / 3);

        const monthSelects = [document.getElementById("dishCustomMonth"), document.getElementById("revenueCustomMonth")];
        const quarterSelects = [document.getElementById("dishQuarter"), document.getElementById("revenueQuarter")];

        // Sinh option tháng
        monthSelects.forEach(sel => {
            sel.innerHTML = ""; // clear cũ
            for (let m = 1; m <= currentMonth; m++) {
                const opt = document.createElement("option");
                opt.value = m;
                opt.textContent = `Tháng ${m}`;
                sel.appendChild(opt);
            }
        });

        // Sinh option quý
        quarterSelects.forEach(sel => {
            sel.innerHTML = "";
            for (let q = 1; q <= currentQuarter; q++) {
                const opt = document.createElement("option");
                opt.value = q;
                opt.textContent = `Quý ${q}`;
                sel.appendChild(opt);
            }
        });
    }

    function loadRevenueSummary() {
        fetch(`/api/owner/${restaurantId}/stats/revenue`)
            .then(res => res.json())
            .then(data => {
                document.getElementById("revenue-today").textContent = data.today.toLocaleString() + " đ";
                document.getElementById("revenue-month").textContent = data.month.toLocaleString() + " đ";
            });
    }

    function loadDishDonut(mode = "day", month = null, quarter = null) {
        let url = `/api/owner/${restaurantId}/stats/dishes?mode=${mode}`;
        if (mode === "custom_month") url += `&month=${month}`;
        if (mode === "quarter") url += `&quarter=${quarter}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                const ctx = document.getElementById("dishDonutChart").getContext("2d");
                if (donutChart) donutChart.destroy();
                donutChart = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: data.map(d => d.dish),
                        datasets: [{
                            data: data.map(d => d.quantity),
                            backgroundColor: [
                                "#FF6384", "#36A2EB", "#FFCE56",
                                "#4BC0C0", "#9966FF", "#FF9F40"
                            ]
                        }]
                    }
                });
            });
    }

    function loadRevenueLine(mode = "day", month = null, quarter = null) {
        let url = `/api/owner/${restaurantId}/stats/revenue_line?mode=${mode}`;
        if (mode === "custom_month") url += `&month=${month}`;
        if (mode === "quarter") url += `&quarter=${quarter}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                const ctx = document.getElementById("revenueLineChart").getContext("2d");
                if (lineChart) lineChart.destroy();
                lineChart = new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: data.map(d => d.label),
                        datasets: [{
                            label: "Doanh thu (đ)",
                            data: data.map(d => d.revenue),
                            borderColor: "#36A2EB",
                            fill: false,
                            tension: 0.3
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function (value) {
                                        return value.toLocaleString() + " đ";
                                    }
                                }
                            }
                        }
                    }
                });
            });
    }

    // ======== Event listeners ========
    const dishModeSel = document.getElementById("dishDonutMode");
    const dishMonthSel = document.getElementById("dishCustomMonth");
    const dishQuarterSel = document.getElementById("dishQuarter");

    dishModeSel.addEventListener("change", e => {
        const mode = e.target.value;
        dishMonthSel.style.display = (mode === "custom_month") ? "inline-block" : "none";
        dishQuarterSel.style.display = (mode === "quarter") ? "inline-block" : "none";

        if (mode === "custom_month") loadDishDonut("custom_month", dishMonthSel.value);
        else if (mode === "quarter") loadDishDonut("quarter", null, dishQuarterSel.value);
        else loadDishDonut(mode);
    });
    dishMonthSel.addEventListener("change", e => {
        loadDishDonut("custom_month", e.target.value);
    });
    dishQuarterSel.addEventListener("change", e => {
        loadDishDonut("quarter", null, e.target.value);
    });

    const revModeSel = document.getElementById("revenueLineMode");
    const revMonthSel = document.getElementById("revenueCustomMonth");
    const revQuarterSel = document.getElementById("revenueQuarter");

    revModeSel.addEventListener("change", e => {
        const mode = e.target.value;
        revMonthSel.style.display = (mode === "custom_month") ? "inline-block" : "none";
        revQuarterSel.style.display = (mode === "quarter") ? "inline-block" : "none";

        if (mode === "custom_month") loadRevenueLine("custom_month", revMonthSel.value);
        else if (mode === "quarter") loadRevenueLine("quarter", null, revQuarterSel.value);
        else loadRevenueLine(mode);
    });
    revMonthSel.addEventListener("change", e => {
        loadRevenueLine("custom_month", e.target.value);
    });
    revQuarterSel.addEventListener("change", e => {
        loadRevenueLine("quarter", null, e.target.value);
    });

    // ======== Init ========
    populateMonthQuarterSelects();
    loadRevenueSummary();
    loadDishDonut("day");
    loadRevenueLine("day");
});
