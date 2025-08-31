document.addEventListener('DOMContentLoaded', function() {
    // Handle toggle attendance buttons
    document.querySelectorAll('.toggle-attendance').forEach(button => {
        button.addEventListener('click', function() {
            const attendanceId = this.dataset.attendanceId;
            const studentName = this.dataset.studentName;
            const isPresent = this.dataset.isPresent === '1';
            const newStatus = !isPresent;
            const button = this;
            
            if (confirm(`Are you sure you want to mark ${studentName} as ${newStatus ? 'present' : 'absent'}?`)) {
                // Make AJAX call to update attendance
                fetch(`/faculty/mark_attendance/${attendanceId}/${newStatus ? 1 : 0}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update the button and row
                        const row = button.closest('tr');
                        const statusCell = row.querySelector('td:nth-child(3)');
                        const timeInCell = row.querySelector('td:nth-child(4)');
                        
                        // Update status badge
                        statusCell.innerHTML = `<span class="badge ${data.is_present ? 'bg-success' : 'bg-danger'}">
                            ${data.is_present ? 'Present' : 'Absent'}
                        </span>`;
                        
                        // Update time in if the cell exists
                        if (timeInCell) {
                            timeInCell.textContent = data.time_in || '-';
                        }
                        
                        // Update button
                        button.innerHTML = `<i class="fas ${data.is_present ? 'fa-times' : 'fa-check'}"></i>
                            ${data.is_present ? 'Mark Absent' : 'Mark Present'}`;
                        button.className = `btn btn-sm ${data.is_present ? 'btn-outline-danger' : 'btn-outline-success'} toggle-attendance`;
                        button.dataset.isPresent = data.is_present ? '1' : '0';
                        
                        // Show success message
                        alert(data.message);
                    } else {
                        // Show error message
                        alert('Error: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred. Please try again.');
                });
            }
        });
    });
    
    // Load students for manual attendance if on that page
    const studentTableBody = document.getElementById('studentTableBody');
    const timetableIdElement = document.getElementById('timetableId');
    
    if (studentTableBody && timetableIdElement) {
        const timetableId = timetableIdElement.value;
        
        // Fetch student data
        fetch(`/faculty/attendance/get_students/${timetableId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear loading indicator
                    studentTableBody.innerHTML = '';
                    
                    if (data.students.length === 0) {
                        // No students found
                        studentTableBody.innerHTML = `
                            <tr>
                                <td colspan="4" class="text-center">
                                    <i class="fas fa-users text-muted mb-3" style="font-size: 2rem;"></i>
                                    <h5 class="text-muted">No students found for this course</h5>
                                    <p>Students must be enrolled in the course to appear here</p>
                                </td>
                            </tr>
                        `;
                        return;
                    }
                    
                    // Populate student table
                    data.students.forEach(student => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${student.roll_number}</td>
                            <td>${student.name}</td>
                            <td>
                                <span class="badge ${student.is_present ? 'bg-success' : 'bg-danger'}">
                                    ${student.is_present ? 'Present' : 'Absent'}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-sm ${student.is_present ? 'btn-outline-danger' : 'btn-outline-success'} toggle-attendance"
                                        data-attendance-id="${student.attendance_id}"
                                        data-student-name="${student.name}"
                                        data-is-present="${student.is_present ? '1' : '0'}">
                                    <i class="fas ${student.is_present ? 'fa-times' : 'fa-check'}"></i>
                                    ${student.is_present ? 'Mark Absent' : 'Mark Present'}
                                </button>
                            </td>
                        `;
                        studentTableBody.appendChild(row);
                    });
                    
                    // Setup toggle attendance buttons
                    document.querySelectorAll('.toggle-attendance').forEach(button => {
                        button.addEventListener('click', function() {
                            const attendanceId = this.dataset.attendanceId;
                            const studentName = this.dataset.studentName;
                            const isPresent = this.dataset.isPresent === '1';
                            const newStatus = !isPresent;
                            const button = this;
                            
                            if (confirm(`Are you sure you want to mark ${studentName} as ${newStatus ? 'present' : 'absent'}?`)) {
                                // Make AJAX call to update attendance
                                fetch(`/faculty/mark_attendance/${attendanceId}/${newStatus ? 1 : 0}`, {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                    }
                                })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        // Update the button and row
                                        const row = button.closest('tr');
                                        const statusCell = row.querySelector('td:nth-child(3)');
                                        
                                        // Update status badge
                                        statusCell.innerHTML = `<span class="badge ${data.is_present ? 'bg-success' : 'bg-danger'}">
                                            ${data.is_present ? 'Present' : 'Absent'}
                                        </span>`;
                                        
                                        // Update button
                                        button.innerHTML = `<i class="fas ${data.is_present ? 'fa-times' : 'fa-check'}"></i>
                                            ${data.is_present ? 'Mark Absent' : 'Mark Present'}`;
                                        button.className = `btn btn-sm ${data.is_present ? 'btn-outline-danger' : 'btn-outline-success'} toggle-attendance`;
                                        button.dataset.isPresent = data.is_present ? '1' : '0';
                                        
                                        // Show success message
                                        alert(data.message);
                                    } else {
                                        // Show error message
                                        alert('Error: ' + data.message);
                                    }
                                })
                                .catch(error => {
                                    console.error('Error:', error);
                                    alert('An error occurred. Please try again.');
                                });
                            }
                        });
                    });
                } else {
                    // Show error
                    studentTableBody.innerHTML = `
                        <tr>
                            <td colspan="4" class="text-center text-danger">
                                <i class="fas fa-exclamation-triangle mb-3" style="font-size: 2rem;"></i>
                                <h5>Error loading students</h5>
                                <p>${data.message || 'An unknown error occurred'}</p>
                            </td>
                        </tr>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                studentTableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">
                            <i class="fas fa-exclamation-triangle mb-3" style="font-size: 2rem;"></i>
                            <h5>Error loading students</h5>
                            <p>Could not connect to the server. Please try again.</p>
                        </td>
                    </tr>
                `;
            });
    }
});
