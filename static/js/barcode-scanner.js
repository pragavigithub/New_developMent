// Barcode Scanner Class
class BarcodeScanner {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanning = false;
        this.onScanCallback = null;
        this.initializeQuagga();
    }

    initializeQuagga() {
        // QuaggaJS configuration for barcode scanning
        this.quaggaConfig = {
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: null,
                constraints: {
                    width: 640,
                    height: 480,
                    facingMode: "environment"
                }
            },
            locator: {
                patchSize: "medium",
                halfSample: true
            },
            numOfWorkers: 2,
            decoder: {
                readers: [
                    "code_128_reader",
                    "ean_reader",
                    "ean_8_reader",
                    "code_39_reader",
                    "code_39_vin_reader",
                    "codabar_reader",
                    "upc_reader",
                    "upc_e_reader",
                    "i2of5_reader"
                ]
            },
            locate: true
        };
    }

    async startScan(videoElement, onScanCallback) {
        try {
            this.video = videoElement;
            this.onScanCallback = onScanCallback;
            
            // Check if camera is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Camera not available');
            }

            // Request camera permission
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            });

            this.video.srcObject = this.stream;
            this.video.play();

            // Initialize QuaggaJS
            this.quaggaConfig.inputStream.target = this.video;
            
            Quagga.init(this.quaggaConfig, (err) => {
                if (err) {
                    console.error('QuaggaJS initialization error:', err);
                    this.fallbackToManualInput();
                    return;
                }
                
                console.log('QuaggaJS initialized successfully');
                Quagga.start();
                this.scanning = true;
                
                // Set up barcode detection
                Quagga.onDetected(this.onBarcodeDetected.bind(this));
            });

        } catch (error) {
            console.error('Error starting barcode scanner:', error);
            this.fallbackToManualInput();
        }
    }

    onBarcodeDetected(result) {
        if (this.onScanCallback && result.codeResult) {
            const code = result.codeResult.code;
            console.log('Barcode detected:', code);
            
            // Stop scanning temporarily to prevent multiple detections
            this.stopScan();
            
            // Call the callback with the scanned code
            this.onScanCallback(code);
            
            // Provide audio feedback
            this.playBeep();
        }
    }

    stopScan() {
        if (this.scanning) {
            Quagga.stop();
            this.scanning = false;
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
    }

    fallbackToManualInput() {
        // Show manual input modal when camera fails
        const modalHtml = `
            <div class="modal fade" id="manualInputModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Manual Barcode Entry</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="manualBarcode" class="form-label">Enter Barcode:</label>
                                <input type="text" class="form-control" id="manualBarcode" placeholder="Scan or type barcode">
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="submitManualBarcode()">Submit</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('manualInputModal'));
        modal.show();
        
        // Focus on input field
        document.getElementById('manualBarcode').focus();
        
        // Handle Enter key
        document.getElementById('manualBarcode').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitManualBarcode();
            }
        });
    }

    playBeep() {
        // Create audio context for beep sound
        if ('AudioContext' in window || 'webkitAudioContext' in window) {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.3;
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
        }
    }

    // QR Code scanning capability
    async scanQRCode(videoElement, onScanCallback) {
        try {
            const qrScanner = new QrScanner(videoElement, result => {
                console.log('QR Code detected:', result);
                onScanCallback(result);
                qrScanner.stop();
            });
            
            await qrScanner.start();
            return qrScanner;
        } catch (error) {
            console.error('QR Scanner error:', error);
            this.fallbackToManualInput();
        }
    }

    // Parse different barcode formats
    parseBarcode(code) {
        // Basic parsing - can be extended based on requirements
        const result = {
            code: code,
            type: 'unknown',
            itemCode: null,
            batchNumber: null,
            expirationDate: null,
            serialNumber: null
        };

        // Check for custom format: ITEM_BATCH_EXPIRY_SERIAL
        if (code.includes('_')) {
            const parts = code.split('_');
            if (parts.length >= 2) {
                result.itemCode = parts[0];
                result.type = 'custom';
                
                if (parts.length >= 3) {
                    result.batchNumber = parts[1];
                }
                
                if (parts.length >= 4) {
                    // Parse expiration date (YYYYMMDD format)
                    const expiry = parts[2];
                    if (expiry.length === 8) {
                        result.expirationDate = new Date(
                            expiry.substring(0, 4),
                            parseInt(expiry.substring(4, 6)) - 1,
                            expiry.substring(6, 8)
                        );
                    }
                }
                
                if (parts.length >= 5) {
                    result.serialNumber = parts[3];
                }
            }
        }

        return result;
    }

    // Generate barcode for items
    generateBarcode(itemCode, batchNumber = null, expirationDate = null, serialNumber = null) {
        let barcode = `ITM_${itemCode}`;
        
        if (batchNumber) {
            barcode += `_${batchNumber}`;
        }
        
        if (expirationDate) {
            const expiry = expirationDate.toISOString().slice(0, 10).replace(/-/g, '');
            barcode += `_${expiry}`;
        }
        
        if (serialNumber) {
            barcode += `_${serialNumber}`;
        }
        
        // Add timestamp for uniqueness
        barcode += `_${Date.now()}`;
        
        return barcode;
    }

    // Check camera permissions
    async checkCameraPermissions() {
        try {
            const permissions = await navigator.permissions.query({ name: 'camera' });
            return permissions.state === 'granted';
        } catch (error) {
            console.error('Error checking camera permissions:', error);
            return false;
        }
    }

    // Request camera permissions
    async requestCameraPermissions() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
            return true;
        } catch (error) {
            console.error('Camera permission denied:', error);
            return false;
        }
    }
}

// Global function for manual barcode submission
function submitManualBarcode() {
    const input = document.getElementById('manualBarcode');
    const code = input.value.trim();
    
    if (code) {
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('manualInputModal'));
        modal.hide();
        
        // Call the callback if available
        if (window.barcodeScanner && window.barcodeScanner.onScanCallback) {
            window.barcodeScanner.onScanCallback(code);
        }
    }
}

// Initialize global barcode scanner
document.addEventListener('DOMContentLoaded', () => {
    window.barcodeScanner = new BarcodeScanner();
});

// Scanner utility functions
function startBarcodeScanner(videoElementId, callback) {
    const videoElement = document.getElementById(videoElementId);
    if (videoElement && window.barcodeScanner) {
        window.barcodeScanner.startScan(videoElement, callback);
    }
}

function stopBarcodeScanner() {
    if (window.barcodeScanner) {
        window.barcodeScanner.stopScan();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BarcodeScanner;
}
