let userOwnerChartInstance = null;
let transactionChartInstance = null;

// ========== User & Owner Chart ==========
function loadUserOwnerChart() {
    const period = document.getElementById("userOwnerPeriod").value;
    const year = new Date().getFullYear(); 

    fetch(`/admin/api/stats/users-owners?period=${period}&year=${year}`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById("userOwnerChart").getContext("2d");

            // xóa chart cũ nếu đã tồn tại
            if (userOwnerChartInstance) {
                userOwnerChartInstance.destroy();
            }

            userOwnerChartInstance = new Chart(ctx, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [
                        { label: "User mới", data: data.users, borderColor: "#36A2EB", fill: false, tension: 0.3 },
                        { label: "Owner mới", data: data.owners, borderColor: "#FF6384", fill: false, tension: 0.3 }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: "top" } }
                }
            });
        });
}

// ========== Transaction Chart ==========
function loadTransactionChart() {
    const period = document.getElementById("transactionPeriod").value;
    const year = new Date().getFullYear(); // dùng năm hiện tại

    fetch(`/admin/api/stats/transactions?period=${period}&year=${year}`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById("transactionChart").getContext("2d");

            if (transactionChartInstance) {
                transactionChartInstance.destroy();
            }

            transactionChartInstance = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Giao dịch thành công",
                            data: data.transactions,
                            backgroundColor: "#4BC0C0"
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        });
}

// ========== Event Listeners ==========
document.addEventListener("DOMContentLoaded", () => {
    loadUserOwnerChart();
    loadTransactionChart();

    document.getElementById("userOwnerPeriod").addEventListener("change", loadUserOwnerChart);

    document.getElementById("transactionPeriod").addEventListener("change", loadTransactionChart);
});
