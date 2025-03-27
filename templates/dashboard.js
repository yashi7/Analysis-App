// Function to get unique values for a specific key from the summary data
function getUniqueValues(key) {
    const uniqueValues = new Set();
    summaryData.forEach(item => {
        if (item[key]) uniqueValues.add(item[key]);
    });
    return Array.from(uniqueValues).sort();
}

// Populate filter dropdowns
function populateFilters() {
    const serviceTypeFilter = document.getElementById('serviceTypeFilter');
    const zoneFilter = document.getElementById('zoneFilter');
    const weightClassFilter = document.getElementById('weightClassFilter');

    getUniqueValues('Service Type Offered').forEach(service => {
        const option = new Option(service, service);
        serviceTypeFilter.appendChild(option);
    });

    getUniqueValues('Zone').forEach(zone => {
        const option = new Option(zone, zone);
        zoneFilter.appendChild(option);
    });

    getUniqueValues('Weight Class').forEach(weight => {
        const option = new Option(weight, weight);
        weightClassFilter.appendChild(option);
    });
}

// Chart initialization
const ctx = document.getElementById('totalSpendChart').getContext('2d');
let totalSpendChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'Total Spend',
            data: [],
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: { beginAtZero: true }
        }
    }
});

// Function to update chart based on filters
function updateChart() {
    const serviceType = document.getElementById('serviceTypeFilter').value;
    const zone = document.getElementById('zoneFilter').value;
    const weightClass = document.getElementById('weightClassFilter').value;

    const filteredData = summaryData.filter(item => {
        return (serviceType === 'all' || item['Service Type Offered'] === serviceType) &&
               (zone === 'all' || item.Zone === zone) &&
               (weightClass === 'all' || item['Weight Class'] === weightClass);
    });

    const groupedData = {};
    filteredData.forEach(item => {
        const service = item['Service Type Offered'];
        if (!groupedData[service]) groupedData[service] = 0;
        groupedData[service] += item.Total_Spend;
    });

    totalSpendChart.data.labels = Object.keys(groupedData);
    totalSpendChart.data.datasets[0].data = Object.values(groupedData);
    totalSpendChart.update();
}

// Add event listeners
document.addEventListener('DOMContentLoaded', function () {
    populateFilters();
    updateChart();

    document.getElementById('serviceTypeFilter').addEventListener('change', updateChart);
    document.getElementById('zoneFilter').addEventListener('change', updateChart);
    document.getElementById('weightClassFilter').addEventListener('change', updateChart);
});
