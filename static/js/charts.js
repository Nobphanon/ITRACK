// Dashboard Charts - ITRACK
// This file handles Chart.js initialization for the dashboard

document.addEventListener('DOMContentLoaded', function () {
    initCharts();
});

function initCharts() {
    // Get chart data from DOM data attributes
    const chartDataEl = document.getElementById('chartData');
    if (!chartDataEl) return;

    const total = parseInt(chartDataEl.dataset.total) || 0;
    const onTrack = parseInt(chartDataEl.dataset.onTrack) || 0;
    const nearDeadline = parseInt(chartDataEl.dataset.nearDeadline) || 0;
    const overdue = parseInt(chartDataEl.dataset.overdue) || 0;

    const fundingData = JSON.parse(chartDataEl.dataset.funding || '{}');

    // Theme detection
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#e2e8f0' : '#1e293b';

    Chart.defaults.color = textColor;

    // Deadline Status Distribution Doughnut Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['ทั้งหมด', 'ปกติ', 'ใกล้ครบกำหนด', 'เกินกำหนด'],
                datasets: [{
                    data: [total, onTrack, nearDeadline, overdue],
                    backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 15, usePointStyle: true, pointStyle: 'circle' }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} โครงการ (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const statusMap = ['', 'On Track', 'Near Deadline', 'Overdue'];
                        const status = statusMap[index];

                        // Navigate to dashboard with status filter
                        if (index === 0) {
                            // All projects - no filter
                            window.location.href = '/dashboard';
                        } else {
                            window.location.href = `/dashboard?status=${encodeURIComponent(status)}`;
                        }
                    }
                }
            }
        });
    }

    // Funding by Affiliation Bar Chart (Vertical)
    const fundingCtx = document.getElementById('fundingChart');
    if (fundingCtx && Object.keys(fundingData).length > 0) {
        const labels = Object.keys(fundingData);
        const values = Object.values(fundingData);

        new Chart(fundingCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'งบประมาณ (บาท)',
                    data: values,
                    backgroundColor: 'rgba(56, 189, 248, 0.8)',  // Sky blue
                    borderColor: 'rgba(14, 165, 233, 1)',        // Darker sky blue
                    borderWidth: 2,
                    borderRadius: 8,
                    maxBarThickness: 50,
                    hoverBackgroundColor: 'rgba(14, 165, 233, 0.9)',
                    hoverBorderColor: 'rgba(2, 132, 199, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return new Intl.NumberFormat('th-TH').format(context.raw) + ' บาท';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { display: true, color: 'rgba(0,0,0,0.1)' },
                        ticks: {
                            callback: function (value) {
                                return new Intl.NumberFormat('th-TH', { notation: 'compact' }).format(value);
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0
                        }
                    }
                }
            }
        });
    }
}
