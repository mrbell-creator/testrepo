document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const hexForm = document.getElementById('hex-form');
    const hexInput = document.getElementById('hex-input');
    const tankHeightInput = document.getElementById('tank-height');
    const resultsContainer = document.getElementById('results-container');
    const closeResultsBtn = document.getElementById('close-results');
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    const exampleHexButtons = document.querySelectorAll('.example-hex');
    
    // Initialize any charts or interactive elements
    initializeApp();
    
    // Form submission handling
    hexForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const hexString = hexInput.value.trim();
        const tankHeight = parseFloat(tankHeightInput.value);
        
        if (!hexString) {
            showError('Please enter a hex string');
            return;
        }
        
        // Validate hex string format - basic validation
        if (!/^[0-9A-Fa-f\s]+$/.test(hexString)) {
            showError('Invalid hex string. Only hexadecimal characters (0-9, A-F) are allowed.');
            return;
        }
        
        parseHexString(hexString, tankHeight);
    });
    
    // Close results button
    closeResultsBtn.addEventListener('click', function() {
        resultsContainer.classList.add('d-none');
    });
    
    // Example hex string buttons
    exampleHexButtons.forEach(button => {
        button.addEventListener('click', function() {
            hexInput.value = this.textContent.trim();
            hexForm.dispatchEvent(new Event('submit'));
        });
    });

    // Initialize app functionality
    function initializeApp() {
        // Nothing to initialize at this point
    }
    
    // Send hex string to server for parsing
    function parseHexString(hexString, tankHeight) {
        fetch('/parse', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                hex_string: hexString,
                tank_height: tankHeight
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayResults(data.data, tankHeight);
                errorAlert.classList.add('d-none');
            } else {
                showError(data.error);
                resultsContainer.classList.add('d-none');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('An error occurred while processing your request. Please try again.');
            resultsContainer.classList.add('d-none');
        });
    }
    
    // Display the parsed results
    function displayResults(data, tankHeight) {
        // Show results container
        resultsContainer.classList.remove('d-none');
        
        // Update level visualizations
        updateTankVisualization(data);
        
        // Update key metrics
        updateKeyMetrics(data);
        
        // Update detailed information
        updateDetailedInfo(data, tankHeight);
        
        // Update advertisement peaks
        updatePeaksData(data.advertisement_peaks);
        
        // Show raw JSON data
        document.getElementById('json-data').textContent = JSON.stringify(data, null, 2);
    }
    
    // Update the tank visualization
    function updateTankVisualization(data) {
        const tankFill = document.getElementById('tank-fill');
        const levelValue = document.getElementById('level-value');
        
        if (data.is_empty) {
            // Empty tank
            tankFill.style.height = '0%';
            levelValue.innerHTML = '<span class="status-empty">Empty</span>';
        } else {
            // Calculate fill percentage (capped at 100%)
            const fillPercentage = Math.min(data.percentage, 100);
            tankFill.style.height = `${fillPercentage}%`;
            
            // Set color based on level
            if (fillPercentage < 20) {
                tankFill.style.background = 'linear-gradient(to bottom, var(--bs-danger) 0%, var(--bs-danger-rgb) 100%)';
            } else if (fillPercentage < 40) {
                tankFill.style.background = 'linear-gradient(to bottom, var(--bs-warning) 0%, var(--bs-warning-rgb) 100%)';
            } else {
                tankFill.style.background = 'linear-gradient(to bottom, var(--bs-success) 0%, var(--bs-success-rgb) 100%)';
            }
            
            // Update text
            levelValue.innerHTML = `<span class="${getStatusClass(fillPercentage)}">${data.level_cm.toFixed(2)} cm</span>`;
        }
    }
    
    // Update key metrics display
    function updateKeyMetrics(data) {
        // Battery
        const batteryValue = document.getElementById('battery-value');
        const batteryVoltage = data.battery_voltage;
        const batteryStatus = getBatteryStatus(batteryVoltage);
        batteryValue.innerHTML = `<i class="${batteryStatus.icon}"></i> ${batteryVoltage.toFixed(2)}V`;
        batteryValue.className = 'metric-value ' + batteryStatus.class;
        
        // Temperature
        const temperatureValue = document.getElementById('temperature-value');
        const tempC = data.temperature_c;
        const tempIcon = tempC < 0 ? 'fa-thermometer-empty' : 
                      tempC < 10 ? 'fa-thermometer-quarter' :
                      tempC < 20 ? 'fa-thermometer-half' :
                      tempC < 30 ? 'fa-thermometer-three-quarters' : 'fa-thermometer-full';
        temperatureValue.innerHTML = `<i class="fas ${tempIcon}"></i> ${tempC.toFixed(1)}°C`;
        
        // Hardware
        const hardwareValue = document.getElementById('hardware-value');
        hardwareValue.innerHTML = `<i class="fas fa-microchip"></i> ${data.hardware_family}`;
        
        // Percentage
        const percentageValue = document.getElementById('percentage-value');
        if (data.is_empty) {
            percentageValue.innerHTML = '<i class="fas fa-percentage"></i> Empty';
            percentageValue.className = 'metric-value status-empty';
        } else {
            percentageValue.innerHTML = `<i class="fas fa-percentage"></i> ${data.percentage}%`;
            percentageValue.className = 'metric-value ' + getStatusClass(data.percentage);
        }
    }
    
    // Update detailed information
    function updateDetailedInfo(data, tankHeight) {
        // Sensor Details
        document.getElementById('hw-id').textContent = data.hardware_id;
        document.getElementById('hw-version').textContent = data.hardware_version;
        document.getElementById('slow-update').textContent = data.slow_update ? 'Yes' : 'No';
        document.getElementById('sync-pressed').textContent = data.sync_pressed ? 'Yes' : 'No';
        document.getElementById('header-value').textContent = data.header;
        document.getElementById('mfr-header').textContent = data.manufacturer_header;
        document.getElementById('accelo-value').textContent = `X: ${data.accelerometer.x}, Y: ${data.accelerometer.y}`;
        document.getElementById('battery-raw').textContent = data.battery_raw;
        
        // Level Measurements
        document.getElementById('tof-value').textContent = `${data.tof.toFixed(8)} seconds`;
        document.getElementById('level-inches').textContent = data.is_empty ? 'Empty' : `${data.level_inches.toFixed(2)} inches`;
        document.getElementById('level-cm').textContent = data.is_empty ? 'Empty' : `${data.level_cm.toFixed(2)} cm`;
        document.getElementById('tank-status').textContent = data.is_empty ? 'Empty' : 'Contains liquid';
        document.getElementById('tank-height-value').textContent = `${tankHeight.toFixed(3)} m`;
        document.getElementById('temp-raw').textContent = data.temperature_raw;
        document.getElementById('temp-celsius').textContent = `${data.temperature_c.toFixed(1)} °C`;
        document.getElementById('percentage-full').textContent = data.is_empty ? 'Empty' : `${data.percentage}%`;
    }
    
    // Update peaks data and chart
    function updatePeaksData(peaks) {
        const peaksData = document.getElementById('peaks-data');
        
        if (!peaks || peaks.length === 0) {
            peaksData.textContent = 'No peak data available';
            return;
        }
        
        peaksData.textContent = JSON.stringify(peaks, null, 2);
        
        // Update or create the peaks chart
        updatePeaksChart(peaks);
    }
    
    // Create or update a chart showing advertisement peaks
    function updatePeaksChart(peaks) {
        const ctx = document.getElementById('peaks-chart').getContext('2d');
        
        // Extract data for the chart
        const labels = peaks.map(peak => peak.i / 2); // Time value
        const amplitudes = peaks.map(peak => peak.a);  // Amplitude
        
        // Destroy previous chart if it exists
        if (peaksChart) {
            peaksChart.destroy();
        }
        
        // Create a new chart
        peaksChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Amplitude',
                    data: amplitudes,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Amplitude'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Advertisement Peaks'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Time: ${context.label}, Amplitude: ${context.raw}`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Display error message
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
    }
    
    // Helper: Get battery status info
    function getBatteryStatus(voltage) {
        if (voltage >= 3.0) {
            return { icon: 'fas fa-battery-full', class: 'status-good' };
        } else if (voltage >= 2.7) {
            return { icon: 'fas fa-battery-three-quarters', class: 'status-good' };
        } else if (voltage >= 2.5) {
            return { icon: 'fas fa-battery-half', class: 'status-warning' };
        } else if (voltage >= 2.3) {
            return { icon: 'fas fa-battery-quarter', class: 'status-warning' };
        } else {
            return { icon: 'fas fa-battery-empty', class: 'status-danger' };
        }
    }
    
    // Helper: Get status class based on percentage
    function getStatusClass(percentage) {
        if (percentage <= 10) {
            return 'status-danger';
        } else if (percentage <= 25) {
            return 'status-warning';
        } else {
            return 'status-good';
        }
    }
});
