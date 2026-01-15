// Dashboard Charts - ITRACK Enhanced
// This file handles Chart.js initialization with improved visualizations

document.addEventListener('DOMContentLoaded', function () {
    initCharts();

    // Re-initialize charts when theme changes
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            setTimeout(initCharts, 100);
        });
    }
});

// Center Text Plugin for Doughnut Charts
const centerTextPlugin = {
    id: 'centerText',
    beforeDraw: function (chart) {
        if (chart.config.type !== 'doughnut') return;

        const ctx = chart.ctx;
        const width = chart.width;
        const height = chart.height;

        // Get center data from options
        const centerConfig = chart.config.options.plugins?.centerText;
        if (!centerConfig) return;

        ctx.save();

        // Draw main number
        const fontSize = Math.min(width, height) / 5;
        ctx.font = `700 ${fontSize}px Prompt, sans-serif`;
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';

        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        ctx.fillStyle = isDarkMode ? '#ffffff' : '#1e293b';
        ctx.fillText(centerConfig.text, width / 2, height / 2 - 5);

        // Draw label
        const labelSize = Math.min(width, height) / 12;
        ctx.font = `500 ${labelSize}px Prompt, sans-serif`;
        ctx.fillStyle = isDarkMode ? '#94a3b8' : '#64748b';
        ctx.fillText(centerConfig.label || '', width / 2, height / 2 + fontSize / 2 + 5);

        ctx.restore();
    }
};

// Register plugin
Chart.register(centerTextPlugin);

function initCharts() {
    // Destroy existing charts if re-initializing
    Chart.getChart('statusChart')?.destroy();
    Chart.getChart('fundingChart')?.destroy();
    Chart.getChart('upcomingChart')?.destroy();

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
    const gridColor = isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

    Chart.defaults.color = textColor;

    // ==========================================
    // Deadline Status Distribution Doughnut Chart
    // ==========================================
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['ทั้งหมด', 'ปกติ', 'ใกล้ครบกำหนด', 'เกินกำหนด'],
                datasets: [{
                    data: [total, onTrack, nearDeadline, overdue],
                    backgroundColor: [
                        '#6366f1', // Indigo - Total
                        '#10b981', // Green - On Track
                        '#f59e0b', // Amber - Near Deadline
                        '#ef4444'  // Red - Overdue
                    ],
                    borderWidth: 0,
                    hoverOffset: 10,
                    hoverBorderWidth: 3,
                    hoverBorderColor: isDarkMode ? '#1e293b' : '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    animateScale: true
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { weight: '500' }
                        }
                    },
                    tooltip: {
                        backgroundColor: isDarkMode ? '#334155' : '#1e293b',
                        titleFont: { weight: '600' },
                        bodyFont: { size: 13 },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = sum > 0 ? ((value / sum) * 100).toFixed(0) : 0;
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

    // ==========================================
    // Funding by Affiliation Bar Chart
    // ==========================================
    const fundingCtx = document.getElementById('fundingChart');
    if (fundingCtx && Object.keys(fundingData).length > 0) {
        const labels = Object.keys(fundingData);
        const values = Object.values(fundingData);

        // Sort by funding value descending
        const sorted = labels.map((label, i) => ({ label, value: values[i] }))
            .sort((a, b) => b.value - a.value);

        new Chart(fundingCtx, {
            type: 'bar',
            data: {
                labels: sorted.map(s => s.label),
                datasets: [{
                    label: 'งบประมาณ (บาท)',
                    data: sorted.map(s => s.value),
                    backgroundColor: sorted.map((_, i) => {
                        // Gradient colors from blue to teal
                        const colors = ['#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981'];
                        return colors[i % colors.length];
                    }),
                    borderWidth: 0,
                    borderRadius: 6,
                    maxBarThickness: 60,
                    hoverBackgroundColor: '#2563eb'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: labels.length > 5 ? 'y' : 'x',  // Horizontal if many affiliations
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDarkMode ? '#334155' : '#1e293b',
                        titleFont: { weight: '600' },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function (context) {
                                const value = new Intl.NumberFormat('th-TH').format(context.raw);
                                return `งบประมาณ: ${value} บาท`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { display: true, color: gridColor },
                        ticks: {
                            callback: function (value) {
                                if (labels.length > 5) return value;  // Labels visible in horizontal
                                return new Intl.NumberFormat('th-TH', { notation: 'compact' }).format(value);
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0,
                            callback: function (value) {
                                if (labels.length > 5) {
                                    return new Intl.NumberFormat('th-TH', { notation: 'compact' }).format(value);
                                }
                                const label = this.getLabelForValue(value);
                                return label.length > 10 ? label.substring(0, 10) + '...' : label;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const affiliation = sorted[index].label;
                        window.location.href = `/dashboard?aff=${encodeURIComponent(affiliation)}`;
                    }
                }
            }
        });
    }

    // ==========================================
    // Upcoming Deadlines Mini Chart (if container exists)
    // ==========================================
    const upcomingCtx = document.getElementById('upcomingChart');
    if (upcomingCtx) {
        // This chart shows distribution of upcoming deadlines
        new Chart(upcomingCtx, {
            type: 'bar',
            data: {
                labels: ['วันนี้', '1-3 วัน', '4-7 วัน', '8-14 วัน', '15-30 วัน'],
                datasets: [{
                    label: 'จำนวนโครงการ',
                    data: JSON.parse(upcomingCtx.dataset.upcoming || '[0,0,0,0,0]'),
                    backgroundColor: [
                        '#ef4444',  // Today - Red
                        '#f97316',  // 1-3 days - Orange
                        '#f59e0b',  // 4-7 days - Amber
                        '#10b981',  // 8-14 days - Green
                        '#06b6d4'   // 15-30 days - Cyan
                    ],
                    borderWidth: 0,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDarkMode ? '#334155' : '#1e293b',
                        padding: 10,
                        cornerRadius: 6
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { stepSize: 1 }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 10 } }
                    }
                }
            }
        });
    }
}
