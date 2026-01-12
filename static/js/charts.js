// Dashboard Charts - ITRACK
// This file handles Chart.js initialization for the dashboard

document.addEventListener('DOMContentLoaded', function () {
    initCharts();
});

function initCharts() {
    // Get chart data from DOM data attributes
    const chartDataEl = document.getElementById('chartData');
    if (!chartDataEl) return;

    const statusDraft = parseInt(chartDataEl.dataset.draft) || 0;
    const statusInProgress = parseInt(chartDataEl.dataset.inProgress) || 0;
    const statusUnderReview = parseInt(chartDataEl.dataset.underReview) || 0;
    const statusCompleted = parseInt(chartDataEl.dataset.completed) || 0;

    const fundingData = JSON.parse(chartDataEl.dataset.funding || '{}');

    // Theme detection
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#e2e8f0' : '#1e293b';

    Chart.defaults.color = textColor;

    // Status Distribution Doughnut Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Draft', 'In Progress', 'Under Review', 'Completed'],
                datasets: [{
                    data: [statusDraft, statusInProgress, statusUnderReview, statusCompleted],
                    backgroundColor: ['#6b7280', '#3b82f6', '#f59e0b', '#10b981'],
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
                    }
                }
            }
        });
    }

    // Funding by Affiliation Bar Chart
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
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                    barThickness: 40
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
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
                    x: {
                        beginAtZero: true,
                        grid: { display: true, color: 'rgba(0,0,0,0.1)' },
                        ticks: {
                            callback: function (value) {
                                return new Intl.NumberFormat('th-TH', { notation: 'compact' }).format(value);
                            }
                        }
                    },
                    y: { grid: { display: false } }
                }
            }
        });
    }
}
