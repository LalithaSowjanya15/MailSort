// Chart Instances tracking object to prevent canvas overlapping glitches
const activeCharts = {
    priority: null,
    category: null,
    trends: null
};

// Colors matching CSS theme system variables
const ChartTheme = {
    urgent: '#EF4444',
    reply: '#3B82F6',
    read: '#F59E0B',
    ignore: '#64748B',
    
    primary: '#4F46E5',
    accent: '#8B5CF6',
    primaryLight: 'rgba(79, 70, 229, 0.1)',
    primaryBorder: 'rgba(79, 70, 229, 0.8)',
    
    gridLines: '#E2E8F0',
    textMain: '#0F172A',
    textMuted: '#64748B'
};

async function loadAnalyticsData() {
    try {
        const res = await fetch('/api/analytics');
        const data = await res.json();
        
        if (data.success) {
            renderPriorityChart(data.priority_distribution);
            renderCategoryChart(data.category_distribution);
            renderTrendsChart(data.daily_trends);
        }
    } catch (e) {
        console.error("Analytics chart data dispatch failed:", e);
    }
}

// 1. Doughnut Chart: Priority Distribution
function renderPriorityChart(prioData) {
    const ctx = document.getElementById('priorityChart');
    if (!ctx) return;
    
    if (activeCharts.priority) {
        activeCharts.priority.destroy();
    }
    
    // Map labels to custom priority theme colors
    const colors = prioData.labels.map(label => {
        if (label === 'Urgent') return ChartTheme.urgent;
        if (label === 'Reply Now') return ChartTheme.reply;
        if (label === 'Read Later') return ChartTheme.read;
        return ChartTheme.ignore;
    });
    
    activeCharts.priority = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: prioData.labels,
            datasets: [{
                data: prioData.data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        font: { family: 'Inter', size: 12 }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

// 2. Horizontal Bar Chart: Category Distribution
function renderCategoryChart(catData) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    
    if (activeCharts.category) {
        activeCharts.category.destroy();
    }
    
    activeCharts.category = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: catData.labels,
            datasets: [{
                label: 'Emails',
                data: catData.data,
                backgroundColor: ChartTheme.accent,
                borderRadius: 6,
                maxBarThickness: 16
            }]
        },
        options: {
            indexAxis: 'y', // Makes the bar chart horizontal
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: ChartTheme.gridLines },
                    ticks: {
                        stepSize: 1,
                        color: ChartTheme.textMuted,
                        font: { family: 'Inter' }
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: {
                        color: ChartTheme.textMain,
                        font: { family: 'Inter', weight: 500 }
                    }
                }
            }
        }
    });
}

// 3. Spline Line Chart: Daily Volume trends
function renderTrendsChart(trendData) {
    const ctx = document.getElementById('trendsChart');
    if (!ctx) return;
    
    if (activeCharts.trends) {
        activeCharts.trends.destroy();
    }
    
    // Create gradient fill effect under the curve
    const chartContext = ctx.getContext('2d');
    const gradient = chartContext.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.3)');
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.0)');
    
    activeCharts.trends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.labels,
            datasets: [{
                label: 'Received volume',
                data: trendData.data,
                borderColor: ChartTheme.primary,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4, // Curved spline line
                borderWidth: 3,
                pointBackgroundColor: ChartTheme.primary,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: ChartTheme.textMuted,
                        font: { family: 'Inter' }
                    }
                },
                y: {
                    grid: { color: ChartTheme.gridLines },
                    ticks: {
                        stepSize: 1,
                        color: ChartTheme.textMuted,
                        font: { family: 'Inter' }
                    },
                    min: 0
                }
            }
        }
    });
}

// Bind to window to allow app.js calling it upon panel toggle
window.loadAnalyticsData = loadAnalyticsData;
