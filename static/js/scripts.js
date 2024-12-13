document.addEventListener('DOMContentLoaded', () => {
    // Platform Selection Buttons
    const redditBtn = document.getElementById('reddit-btn');
    const chanBtn = document.getElementById('4chan-btn');

    // Selection Panels
    const subredditSelection = document.getElementById('subreddit-selection');
    const boardSelection = document.getElementById('board-selection');

    // Update Visualizations Button
    const updateBtn = document.getElementById('update-btn');

    // Loading Spinner
    // const loadingSpinner = document.getElementById('loading-spinner');

    // Current Platform ('reddit', '4chan', or 'all')
    let currentPlatform = 'reddit';

    // Chart Instances
    let sentimentChart, toxicityChart, averageScoresChart, sentimentScoreChart, keywordCountsChart;

    // Event Listener for Reddit Button
    redditBtn.addEventListener('click', () => {
        currentPlatform = 'reddit';
        redditBtn.classList.add('active');
        chanBtn.classList.remove('active');
        subredditSelection.classList.remove('hidden');
        boardSelection.classList.add('hidden');
        console.log('Switched to Reddit platform');
    });
document.addEventListener('DOMContentLoaded', () => {
    const selectAllSubredditsCheckbox = document.getElementById('select-all-subreddits');
    const subredditCheckboxes = document.querySelectorAll('.subreddit-checkbox:not(#select-all-subreddits)');

    // Handle "All" checkbox
    selectAllSubredditsCheckbox.addEventListener('change', () => {
        const isChecked = selectAllSubredditsCheckbox.checked;
        subredditCheckboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
        });
    });

    // Handle individual checkboxes to update the "All" checkbox
    subredditCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const allChecked = Array.from(subredditCheckboxes).every(cb => cb.checked);
            const noneChecked = Array.from(subredditCheckboxes).every(cb => !cb.checked);

            // Update the "All" checkbox state
            if (allChecked) {
                selectAllSubredditsCheckbox.checked = true;
                selectAllSubredditsCheckbox.indeterminate = false;
            } else if (noneChecked) {
                selectAllSubredditsCheckbox.checked = false;
                selectAllSubredditsCheckbox.indeterminate = false;
            } else {
                selectAllSubredditsCheckbox.checked = false;
                selectAllSubredditsCheckbox.indeterminate = true;
            }
        });
    });
});
    // Event Listener for 4chan Button
    chanBtn.addEventListener('click', () => {
        currentPlatform = '4chan';
        chanBtn.classList.add('active');
        redditBtn.classList.remove('active');
        boardSelection.classList.remove('hidden');
        subredditSelection.classList.add('hidden');
        console.log('Switched to 4chan platform');
    });

    // Event Listener for Update Button
    updateBtn.addEventListener('click', () => {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;

        console.log(`Update clicked: startDate=${startDate}, endDate=${endDate}, platform=${currentPlatform}`);

        // Validation
        if (!startDate || !endDate) {
            alert('Please select both start and end dates.');
            return;
        }

        if (startDate > endDate) {
            alert('Start date cannot be after end date.');
            return;
        }

        // Get Selected Subreddits or Boards
        let selections = [];
        if (currentPlatform === 'reddit') {
            selections = Array.from(document.querySelectorAll('.subreddit-checkbox:checked')).map(checkbox => checkbox.value);
            console.log(`Selected subreddits: ${selections}`);
            if (selections.length === 0) {
                alert('Please select at least one subreddit.');
                return;
            }
        } else {
            selections = Array.from(document.querySelectorAll('.board-checkbox:checked')).map(checkbox => checkbox.value);
            console.log(`Selected boards: ${selections}`);
            if (selections.length === 0) {
                alert('Please select at least one board.');
                return;
            }
        }

        // Show Loading Spinner
        // loadingSpinner.classList.remove('hidden');

        // Fetch Data
        fetchData(currentPlatform, startDate, endDate, selections);
    });

    /**
     * Fetch data from the backend API based on platform and selections
     * @param {string} platform - 'reddit', '4chan', or 'all'
     * @param {string} startDate - Start date in 'YYYY-MM-DD' format
     * @param {string} endDate - End date in 'YYYY-MM-DD' format
     * @param {Array} selections - Array of selected subreddits or boards
     */
    function fetchData(platform, startDate, endDate, selections) {
        let url = '';
        let params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);

        if (platform === 'reddit') {
            url = '/api/reddit/data';
            selections.forEach(sub => params.append('subreddits', sub));
            console.log(`Fetching Reddit data from ${url} with params: ${params.toString()}`);
        } else if (platform === '4chan') {
            url = '/api/4chan/data';
            selections.forEach(board => params.append('boards', board));
            console.log(`Fetching 4chan data from ${url} with params: ${params.toString()}`);
        } else if (platform === 'all') {
            url = '/api/all/data';
            selections.forEach(sub => params.append('subreddits', sub));
            selections.forEach(board => params.append('boards', board));
            console.log(`Fetching All data from ${url} with params: ${params.toString()}`);
        }

        // Fetch data for existing charts
        fetch(`${url}?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API request failed with status ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Fetched Data:', data);
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                // Render existing charts
                renderCharts(platform, data, selections);
                // Fetch and render keyword counts
                fetchKeywordCounts(platform, startDate, endDate, selections);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                alert('An error occurred while fetching data. Check the console for more details.');
            });
    }

    /**
     * Fetch keyword counts from the backend API
     * @param {string} platform - 'reddit', '4chan', or 'all'
     * @param {string} startDate - Start date in 'YYYY-MM-DD' format
     * @param {string} endDate - End date in 'YYYY-MM-DD' format
     * @param {Array} selections - Array of selected subreddits or boards
     */
    function fetchKeywordCounts(platform, startDate, endDate, selections) {
        let url = '/api/word_counts';
        let params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        params.append('platform', platform); // 'reddit', '4chan', or 'all'

        if (platform === 'reddit' || platform === 'all') {
            selections.forEach(sub => params.append('subreddits', sub));
        }

        if (platform === '4chan' || platform === 'all') {
            selections.forEach(board => params.append('boards', board));
        }

        console.log(`Fetching Keyword Counts from ${url} with params: ${params.toString()}`);

        fetch(`${url}?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Keyword Counts API request failed with status ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Fetched Keyword Counts Data:', data);
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                renderKeywordCountsChart(data.keyword_counts);
            })
            .catch(error => {
                console.error('Error fetching keyword counts:', error);
                alert('An error occurred while fetching keyword counts. Check the console for more details.');
            });
    }

    /**
     * Generate a color palette with distinct colors
     * @param {number} numberOfColors - Number of distinct colors needed
     * @returns {Array} - Array of color strings in RGBA format
     */
    function getColorPalette(numberOfColors) {
        const baseColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#2ECC71',
            '#E74C3C', '#3498DB', '#F1C40F', '#9B59B6',
            '#34495E', '#8E44AD', '#16A085', '#D35400',
            '#7F8C8D', '#C0392B', '#2980B9', '#1ABC9C',
            '#BDC3C7', '#95A5A6', '#F39C12', '#27AE60'
        ];
        if (numberOfColors <= baseColors.length) {
            return baseColors.slice(0, numberOfColors);
        } else {
            // Generate additional colors if needed by repeating the base colors
            let colors = [...baseColors];
            while (colors.length < numberOfColors) {
                colors = colors.concat(baseColors);
            }
            return colors.slice(0, numberOfColors);
        }
    }

    /**
     * Render all existing charts based on fetched data and selections
     * @param {string} platform - 'reddit', '4chan', or 'all'
     * @param {Object} data - Data object returned from the backend API
     * @param {Array} selections - Array of selected subreddits or boards
     */
    function renderCharts(platform, data, selections) {
        // Determine the labels based on the first selected subreddit/board
        let labels = [];
        if (selections.length > 0) {
            const firstSelection = selections[0];
            if (data.sentiment_trend[firstSelection] && data.sentiment_trend[firstSelection].dates) {
                labels = data.sentiment_trend[firstSelection].dates;
            }
        }

        // Assign distinct colors for each selection
        const colors = getColorPalette(selections.length);

        // Sentiment Trend Chart Data
        const sentimentDatasets = selections.map((key, index) => ({
            label: key,
            data: data.sentiment_trend[key] ? data.sentiment_trend[key].values : [],
            borderColor: colors[index],
            backgroundColor: colors[index],
            fill: false,
            tension: 0.1
        }));

        // Sentiment * Score Trend Chart Data
        const sentimentScoreDatasets = selections.map((key, index) => ({
            label: key,
            data: data.sentiment_score_trend[key] ? data.sentiment_score_trend[key].values : [],
            borderColor: colors[index],
            backgroundColor: colors[index],
            fill: false,
            tension: 0.1
        }));

        // Toxicity Distribution Chart Data (Stacked Bar)
        const toxicityDatasets = [
            {
                label: 'Non-Toxic',
                data: selections.map(key => data.toxicity_distribution[key] ? data.toxicity_distribution[key].non_toxic : 0),
                backgroundColor: 'rgba(54, 162, 235, 0.7)', // Blue
            },
            {
                label: 'Toxic',
                data: selections.map(key => data.toxicity_distribution[key] ? data.toxicity_distribution[key].toxic : 0),
                backgroundColor: 'rgba(255, 99, 132, 0.7)', // Red
            }
        ];

        // Average Scores Chart Data
        const averageScoresLabels = selections;
        const averageScoresData = selections.map(key => data.average_scores[key] !== undefined ? data.average_scores[key] : 0);
        const averageScoresColors = colors;

        // Sentiment Trend Chart
        const sentimentCtx = document.getElementById('sentiment-chart').getContext('2d');
        if (sentimentChart) sentimentChart.destroy();
        sentimentChart = new Chart(sentimentCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: sentimentDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    },
                    title: {
                        display: true,
                        text: 'Sentiment Trend'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sentiment Score'
                        }
                    }
                }
            }
        });

        // Sentiment * Score Trend Chart
        const sentimentScoreCtx = document.getElementById('sentiment-score-chart').getContext('2d');
        if (sentimentScoreChart) sentimentScoreChart.destroy();
        sentimentScoreChart = new Chart(sentimentScoreCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: sentimentScoreDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    },
                    title: {
                        display: true,
                        text: 'Sentiment * Score Trend'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sentiment * Score'
                        }
                    }
                }
            }
        });

        // Toxicity Distribution Chart (Stacked Bar)
        const toxicityCtx = document.getElementById('toxicity-chart').getContext('2d');
        if (toxicityChart) toxicityChart.destroy();
        toxicityChart = new Chart(toxicityCtx, {
            type: 'bar',
            data: {
                labels: averageScoresLabels,
                datasets: toxicityDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y;
                                return label;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Toxicity Distribution'
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: platform === 'reddit' ? 'Subreddits' : 'Boards'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });

        // Average Scores Chart
        const avgScoresCtx = document.getElementById('average-scores-chart').getContext('2d');
        if (averageScoresChart) averageScoresChart.destroy();
        averageScoresChart = new Chart(avgScoresCtx, {
            type: 'bar',
            data: {
                labels: averageScoresLabels,
                datasets: [{
                    label: 'Average Score',
                    data: averageScoresData,
                    backgroundColor: averageScoresColors
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        enabled: true
                    },
                    title: {
                        display: true,
                        text: 'Average Scores'
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            autoSkip: false,
                            maxRotation: 90,
                            minRotation: 45
                        },
                        title: {
                            display: true,
                            text: platform === 'reddit' ? 'Subreddits' : 'Boards'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Average Score'
                        }
                    }
                }
            }
        });
    }

    /**
     * Render Keyword Counts Chart
     * @param {Object} keywordCounts - Dictionary with dates as keys and positive/negative counts
     */
    function renderKeywordCountsChart(keywordCounts) {
        // Prepare data sorted by date
        const sortedDates = Object.keys(keywordCounts).sort();
        const positiveCounts = sortedDates.map(date => keywordCounts[date]['positive']);
        const negativeCounts = sortedDates.map(date => keywordCounts[date]['negative']);

        // Colors for positive and negative
        const positiveColor = 'rgba(75, 192, 192, 0.7)'; // Teal
        const negativeColor = 'rgba(255, 99, 132, 0.7)'; // Red

        // Keyword Counts Chart Data
        const keywordCountsData = {
            labels: sortedDates,
            datasets: [
                {
                    label: 'Positive Keywords',
                    data: positiveCounts,
                    backgroundColor: positiveColor,
                },
                {
                    label: 'Negative Keywords',
                    data: negativeCounts,
                    backgroundColor: negativeColor,
                }
            ]
        };

        // Destroy existing chart if it exists
        const ctx = document.getElementById('keyword-counts-chart').getContext('2d');
        if (keywordCountsChart) keywordCountsChart.destroy();

        // Create Keyword Counts Chart
        keywordCountsChart = new Chart(ctx, {
            type: 'bar',
            data: keywordCountsData,
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    },
                    title: {
                        display: true,
                        text: 'Keyword Counts Over Time'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        stacked: false,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });
    }

    /**
     * Render all existing charts based on fetched data and selections
     * @param {string} platform - 'reddit', '4chan', or 'all'
     * @param {Object} data - Data object returned from the backend API
     * @param {Array} selections - Array of selected subreddits or boards
     */
    function renderCharts(platform, data, selections) {
        // Determine the labels based on the first selected subreddit/board
        let labels = [];
        if (selections.length > 0) {
            const firstSelection = selections[0];
            if (data.sentiment_trend[firstSelection] && data.sentiment_trend[firstSelection].dates) {
                labels = data.sentiment_trend[firstSelection].dates;
            }
        }

        // Assign distinct colors for each selection
        const colors = getColorPalette(selections.length);

        // Sentiment Trend Chart Data
        const sentimentDatasets = selections.map((key, index) => ({
            label: key,
            data: data.sentiment_trend[key] ? data.sentiment_trend[key].values : [],
            borderColor: colors[index],
            backgroundColor: colors[index],
            fill: false,
            tension: 0.1
        }));

        // Sentiment * Score Trend Chart Data
        const sentimentScoreDatasets = selections.map((key, index) => ({
            label: key,
            data: data.sentiment_score_trend[key] ? data.sentiment_score_trend[key].values : [],
            borderColor: colors[index],
            backgroundColor: colors[index],
            fill: false,
            tension: 0.1
        }));

        // Toxicity Distribution Chart Data (Stacked Bar)
        const toxicityDatasets = [
            {
                label: 'Non-Toxic',
                data: selections.map(key => data.toxicity_distribution[key] ? data.toxicity_distribution[key].non_toxic : 0),
                backgroundColor: 'rgba(54, 162, 235, 0.7)', // Blue
            },
            {
                label: 'Toxic',
                data: selections.map(key => data.toxicity_distribution[key] ? data.toxicity_distribution[key].toxic : 0),
                backgroundColor: 'rgba(255, 99, 132, 0.7)', // Red
            }
        ];

        // Average Scores Chart Data
        const averageScoresLabels = selections;
        const averageScoresData = selections.map(key => data.average_scores[key] !== undefined ? data.average_scores[key] : 0);
        const averageScoresColors = colors;

        // Sentiment Trend Chart
        const sentimentCtx = document.getElementById('sentiment-chart').getContext('2d');
        if (sentimentChart) sentimentChart.destroy();
        sentimentChart = new Chart(sentimentCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: sentimentDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    },
                    title: {
                        display: true,
                        text: 'Sentiment Trend'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sentiment Score'
                        }
                    }
                }
            }
        });

        // Sentiment * Score Trend Chart
        const sentimentScoreCtx = document.getElementById('sentiment-score-chart').getContext('2d');
        if (sentimentScoreChart) sentimentScoreChart.destroy();
        sentimentScoreChart = new Chart(sentimentScoreCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: sentimentScoreDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    },
                    title: {
                        display: true,
                        text: 'Sentiment * Score Trend'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sentiment * Score'
                        }
                    }
                }
            }
        });

        // Toxicity Distribution Chart (Stacked Bar)
        const toxicityCtx = document.getElementById('toxicity-chart').getContext('2d');
        if (toxicityChart) toxicityChart.destroy();
        toxicityChart = new Chart(toxicityCtx, {
            type: 'bar',
            data: {
                labels: averageScoresLabels,
                datasets: toxicityDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y;
                                return label;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Toxicity Distribution'
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: platform === 'reddit' ? 'Subreddits' : 'Boards'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });

        // Average Scores Chart
        const avgScoresCtx = document.getElementById('average-scores-chart').getContext('2d');
        if (averageScoresChart) averageScoresChart.destroy();
        averageScoresChart = new Chart(avgScoresCtx, {
            type: 'bar',
            data: {
                labels: averageScoresLabels,
                datasets: [{
                    label: 'Average Score',
                    data: averageScoresData,
                    backgroundColor: averageScoresColors
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        enabled: true
                    },
                    title: {
                        display: true,
                        text: 'Average Scores'
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            autoSkip: false,
                            maxRotation: 90,
                            minRotation: 45
                        },
                        title: {
                            display: true,
                            text: platform === 'reddit' ? 'Subreddits' : 'Boards'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Average Score'
                        }
                    }
                }
            }
        });
    }

    /**
     * Render Keyword Counts Chart
     * @param {Object} keywordCounts - Dictionary with dates as keys and positive/negative counts
     */
    function renderKeywordCountsChart(keywordCounts) {
        // Prepare data sorted by date
        const sortedDates = Object.keys(keywordCounts).sort();
        const positiveCounts = sortedDates.map(date => keywordCounts[date]['positive']);
        const negativeCounts = sortedDates.map(date => keywordCounts[date]['negative']);

        // Colors for positive and negative
        const positiveColor = 'rgba(75, 192, 192, 0.7)'; // Teal
        const negativeColor = 'rgba(255, 99, 132, 0.7)'; // Red

        // Keyword Counts Chart Data
        const keywordCountsData = {
            labels: sortedDates,
            datasets: [
                {
                    label: 'Positive Keywords',
                    data: positiveCounts,
                    backgroundColor: positiveColor,
                },
                {
                    label: 'Negative Keywords',
                    data: negativeCounts,
                    backgroundColor: negativeColor,
                }
            ]
        };

        // Destroy existing chart if it exists
        const ctx = document.getElementById('keyword-counts-chart').getContext('2d');
        if (keywordCountsChart) keywordCountsChart.destroy();

        // Create Keyword Counts Chart
        keywordCountsChart = new Chart(ctx, {
            type: 'bar',
            data: keywordCountsData,
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y;
                                return label;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Keyword Counts Over Time'
                    }
                },
                scales: {
                    x: {
                        stacked: false,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });
    }
});


