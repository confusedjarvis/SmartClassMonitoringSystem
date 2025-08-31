// Main JavaScript file

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-close alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Camera functions for face recognition
function setupCamera(videoElement) {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function(stream) {
                videoElement.srcObject = stream;
                videoElement.play();
            })
            .catch(function(error) {
                console.error("Error accessing the camera: ", error);
                showCameraError();
            });
    } else {
        console.error("getUserMedia is not supported in this browser");
        showCameraError();
    }
}

function stopCamera(videoElement) {
    if (videoElement.srcObject) {
        const tracks = videoElement.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoElement.srcObject = null;
    }
}

function captureImage(videoElement, canvasElement) {
    // Get the canvas context
    const context = canvasElement.getContext('2d');
    
    // Set canvas dimensions to match video
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    
    // Draw the current video frame onto the canvas
    context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
    
    // Convert canvas to base64 image
    const imageData = canvasElement.toDataURL('image/jpeg');
    
    return imageData;
}

function showCameraError() {
    const errorContainer = document.getElementById('camera-error');
    if (errorContainer) {
        errorContainer.classList.remove('d-none');
    }
}

// Student Registration - Face Capture
function initFaceCapture() {
    const video = document.getElementById('video-capture');
    const canvas = document.getElementById('canvas-capture');
    const captureBtn = document.getElementById('capture-btn');
    const retakeBtn = document.getElementById('retake-btn');
    const faceDataInput = document.getElementById('face_data');
    const previewImage = document.getElementById('preview-image');
    
    if (!video || !canvas) return;
    
    // Start camera
    setupCamera(video);
    
    // Capture button event
    if (captureBtn) {
        captureBtn.addEventListener('click', function() {
            const imageData = captureImage(video, canvas);
            
            // Set the face data in the hidden form field
            if (faceDataInput) {
                faceDataInput.value = imageData;
            }
            
            // Display the captured image
            if (previewImage) {
                previewImage.src = imageData;
                previewImage.classList.remove('d-none');
            }
            
            // Hide video, show preview
            video.classList.add('d-none');
            canvas.classList.remove('d-none');
            
            // Hide capture button, show retake button
            captureBtn.classList.add('d-none');
            if (retakeBtn) {
                retakeBtn.classList.remove('d-none');
            }
        });
    }
    
    // Retake button event
    if (retakeBtn) {
        retakeBtn.addEventListener('click', function() {
            // Clear face data
            if (faceDataInput) {
                faceDataInput.value = '';
            }
            
            // Show video, hide preview
            video.classList.remove('d-none');
            canvas.classList.add('d-none');
            if (previewImage) {
                previewImage.classList.add('d-none');
            }
            
            // Show capture button, hide retake button
            captureBtn.classList.remove('d-none');
            retakeBtn.classList.add('d-none');
        });
    }
}

// Automatic Attendance Capture
function initAutoAttendance() {
    const video = document.getElementById('video-attendance');
    const canvas = document.getElementById('canvas-attendance');
    const captureBtn = document.getElementById('capture-attendance-btn');
    const resultContainer = document.getElementById('recognition-results');
    const timetableId = document.getElementById('timetable-id');
    
    if (!video || !canvas || !captureBtn || !timetableId) return;
    
    // Start camera
    setupCamera(video);
    
    // Capture button event
    captureBtn.addEventListener('click', function() {
        const imageData = captureImage(video, canvas);
        
        // Show loading indicator
        resultContainer.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Processing...</p></div>';
        
        // Send image to server for face recognition
        fetch(`/faculty/auto_attendance/${timetableId.value}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image_data: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let resultsHtml = '<div class="alert alert-success">Successfully recognized students!</div>';
                
                if (data.recognized_students && data.recognized_students.length > 0) {
                    resultsHtml += '<ul class="list-group mt-3">';
                    data.recognized_students.forEach(student => {
                        resultsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center">
                            <span>${student.name} (${student.roll_number})</span>
                            <span class="badge bg-success rounded-pill"><i class="fas fa-check"></i> Present</span>
                        </li>`;
                    });
                    resultsHtml += '</ul>';
                } else {
                    resultsHtml += '<div class="alert alert-warning">No students recognized in the image.</div>';
                }
                
                resultContainer.innerHTML = resultsHtml;
            } else {
                resultContainer.innerHTML = `<div class="alert alert-danger">Error: ${data.message}</div>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultContainer.innerHTML = `<div class="alert alert-danger">An error occurred while processing the image.</div>`;
        });
    });
}

// Clean up resources when leaving the page
window.addEventListener('beforeunload', function() {
    const videoElements = document.querySelectorAll('video');
    videoElements.forEach(video => {
        stopCamera(video);
    });
});
