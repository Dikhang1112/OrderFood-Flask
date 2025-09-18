document.addEventListener("DOMContentLoaded", () => {
    // Gọi API lấy dữ liệu user & owner
//    fetch("/admin/api/stats/users_owners")
//        .then(res => res.json())
//        .then(data => {
//            const ctx = document.getElementById("userOwnerChart").getContext("2d");
//            new Chart(ctx, {
//                type: "line",
//                data: {
//                    labels: data.labels, // ["Tháng 1", "Tháng 2", ...]
//                    datasets: [
//                        {
//                            label: "User mới",
//                            data: data.users,
//                            borderColor: "#36A2EB",
//                            fill: false,
//                            tension: 0.3
//                        },
//                        {
//                            label: "Owner mới",
//                            data: data.owners,
//                            borderColor: "#FF6384",
//                            fill: false,
//                            tension: 0.3
//                        }
//                    ]
//                },
//                options: {
//                    responsive: true,
//                    plugins: {
//                        legend: { position: "top" }
//                    }
//                }
//            });
//        });

    // Gọi API lấy dữ liệu giao dịch thành công
    fetch("/admin/api/stats/transactions")
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById("transactionChart").getContext("2d");
            new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels, // ["Tháng 1", "Tháng 2", ...]
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
});
