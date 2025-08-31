// Auto Attendance Feature with Advanced Face Recognition
let videoStream = null;
let video = null;
let canvas = null;
let captureBtn = null;
let isCapturing = false;

function initAutoAttendance() {
    // Get DOM elements
    video = document.getElementById('video-attendance');
    canvas = document.getElementById('canvas-attendance');
    captureBtn = document.getElementById('capture-attendance-btn');
    
    // Add event listeners
    if (captureBtn) {
        captureBtn.addEventListener('click', captureAttendance);
    }
    
    // Initialize camera
    initCamera();
}

function initCamera() {
    // Check if browser supports getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showCameraError("Your browser doesn't support camera access");
        return;
    }
    
    // Request camera access with preferred settings
    navigator.mediaDevices.getUserMedia({
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user'
        },
        audio: false
    })
    .then(function(stream) {
        videoStream = stream;
        video.srcObject = stream;
        hideCameraError();
    })
    .catch(function(error) {
        console.error("Camera error:", error);
        showCameraError("Could not access the camera. Please check permissions.");
    });
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
        if (video) {
            video.srcObject = null;
        }
    }
}

function showCameraError(message) {
    const errorEl = document.getElementById('camera-error');
    if (errorEl) {
        errorEl.textContent = message || "Camera error occurred";
        errorEl.classList.remove('d-none');
    }
}

function hideCameraError() {
    const errorEl = document.getElementById('camera-error');
    if (errorEl) {
        errorEl.classList.add('d-none');
    }
}

function captureAttendance() {
    // Prevent multiple captures
    if (isCapturing) {
        return;
    }
    
    // Update button state
    isCapturing = true;
    captureBtn.disabled = true;
    captureBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    
    // Draw current video frame to canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get image data as base64
    const imageData = canvas.toDataURL('image/jpeg');
    
    // Get timetable ID
    const timetableId = document.getElementById('timetable-id').value;
    
    // Send to server for processing
    fetch(`/faculty/auto_attendance/${timetableId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image_data: imageData })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Attendance response:", data);
        
        if (data.success) {
            // Show recognized students
            showRecognitionResults(data);
            
            // If annotated image is available, show it
            if (data.annotated_image) {
                showAnnotatedImage(data.annotated_image);
            }
        } else {
            // Show error
            showRecognitionError(data.message || "Failed to process attendance");
        }
    })
    .catch(error => {
        console.error("Error sending capture:", error);
        showRecognitionError("Network error occurred");
    })
    .finally(() => {
        // Reset button state
        isCapturing = false;
        captureBtn.disabled = false;
        captureBtn.innerHTML = '<i class="fas fa-camera me-2"></i>Capture Attendance';
    });
}

function showRecognitionResults(data) {
    const resultsContainer = document.getElementById('recognition-results');
    
    if (!resultsContainer) {
        return;
    }
    
    if (data.recognized_students && data.recognized_students.length > 0) {
        // Create results markup
        let html = `
            <div class="mb-3">
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    ${data.message || `Successfully recognized ${data.recognized_students.length} students`}
                </div>
            </div>
            <div class="recognized-students">
        `;
        
        // Add student list
        html += '<ul class="list-group mb-3">';
        data.recognized_students.forEach(student => {
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${student.name}</strong>
                        <div class="text-muted small">${student.roll_number}</div>
                    </div>
                    <span class="badge bg-success rounded-pill">
                        ${student.confidence ? student.confidence : 'Present'}
                    </span>
                </li>
            `;
        });
        html += '</ul>';
        
        // Include a reload button
        html += `
            <div class="text-center">
                <button type="button" class="btn btn-primary" onclick="captureAttendance()">
                    <i class="fas fa-redo me-2"></i>Capture Again
                </button>
            </div>
        `;
        
        resultsContainer.innerHTML = html;
    } else {
        // No students recognized
        resultsContainer.innerHTML = `
            <div class="alert alert-warning mb-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${data.message || "No students recognized in the image"}
            </div>
            <div class="text-center">
                <button type="button" class="btn btn-primary" onclick="captureAttendance()">
                    <i class="fas fa-redo me-2"></i>Try Again
                </button>
            </div>
        `;
    }
}

function showAnnotatedImage(imageData) {
    // Create image preview container if not exists
    let previewContainer = document.getElementById('annotated-image-container');
    
    if (!previewContainer) {
        // Create container
        previewContainer = document.createElement('div');
        previewContainer.id = 'annotated-image-container';
        previewContainer.className = 'mt-4 text-center';
        
        // Add title
        const title = document.createElement('h5');
        title.className = 'mb-2';
        title.innerHTML = '<i class="fas fa-image me-2"></i>Processed Image';
        previewContainer.appendChild(title);
        
        // Add image element
        const img = document.createElement('img');
        img.id = 'annotated-image';
        img.className = 'img-fluid rounded border';
        img.style.maxHeight = '300px';
        previewContainer.appendChild(img);
        
        // Insert before recognition results
        const resultsContainer = document.getElementById('recognition-results');
        resultsContainer.parentNode.insertBefore(previewContainer, resultsContainer);
    }
    
    // Update image source
    const img = document.getElementById('annotated-image');
    if (img) {
        img.src = imageData;
    }
}

function showRecognitionError(message) {
    const resultsContainer = document.getElementById('recognition-results');
    
    if (resultsContainer) {
        resultsContainer.innerHTML = `
            <div class="alert alert-danger mb-3">
                <i class="fas fa-exclamation-circle me-2"></i>
                ${message || "An error occurred processing the attendance"}
            </div>
            <div class="text-center">
                <button type="button" class="btn btn-primary" onclick="captureAttendance()">
                    <i class="fas fa-redo me-2"></i>Try Again
                </button>
            </div>
        `;
    }
}

// Clean up resources when page is unloaded
window.addEventListener('beforeunload', function() {
    stopCamera();
});
