// index.js - Handles file upload, preview, and result display for index.html

document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const selectedFile = document.getElementById('selectedFile');
    const errorAlert = document.getElementById('errorAlert');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const preview = document.getElementById('preview');

    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            selectedFile.textContent = fileInput.files[0].name;
            const reader = new FileReader();
            reader.onload = function (e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(fileInput.files[0]);
        } else {
            selectedFile.textContent = '';
            preview.style.display = 'none';
        }
    });

    uploadForm.addEventListener('submit', function (e) {
        e.preventDefault();
        errorAlert.style.display = 'none';
        loading.style.display = 'block';
        results.innerHTML = '';

        const formData = new FormData();
        if (fileInput.files.length === 0) {
            errorAlert.textContent = 'Please select a file.';
            errorAlert.style.display = 'block';
            loading.style.display = 'none';
            return;
        }
        formData.append('file', fileInput.files[0]);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            let html = '';
            // Use warnings from API if present
            if (Array.isArray(data.warnings) && data.warnings.length > 0) {
                html += `<div class='error-message'>${data.warnings.join('<br>')}</div>`;
            }
            if (data.error) {
                errorAlert.textContent = data.error;
                errorAlert.style.display = 'block';
            } else {
                if (data.results) {
                    // Build a table with additional columns for Bubble Area and Bubble Circularity
                    html += `<table class='results-table'><thead><tr><th>Q#</th><th>Detected Answer(s)</th><th>Bubbles Detected</th><th>Fill Ratios</th><th>Bubble Area</th><th>Bubble Circularity</th></tr></thead><tbody>`;
                    Object.keys(data.results).sort((a, b) => {
                        // Sort by question number
                        const numA = parseInt(a.replace('question_', ''));
                        const numB = parseInt(b.replace('question_', ''));
                        return numA - numB;
                    }).forEach(key => {
                        const r = data.results[key];
                        // Use detected_answers (array) if present, else fallback to detected_answer
                        let answerDisplay = 'No Answer';
                        let isMultiple = false;
                        if (Array.isArray(r.detected_answers) && r.detected_answers.length > 0) {
                            answerDisplay = r.detected_answers.join(', ');
                            if (r.detected_answers.length > 1) {
                                answerDisplay = `Multiple: ${answerDisplay}`;
                                isMultiple = true;
                            }
                        } else if (r.detected_answer !== undefined && r.detected_answer !== null) {
                            answerDisplay = r.detected_answer;
                        }
                        // Add a class for multiple answers
                        const rowClass = isMultiple ? 'warning' : '';
                        html += `<tr class='${rowClass}'><td>${key.replace('question_', '')}</td><td>${answerDisplay}</td><td>${r.bubbles_detected ?? ''}</td><td>${Array.isArray(r.fill_ratios) ? r.fill_ratios.map(x => x.toFixed(2)).join(', ') : ''}</td><td>${Array.isArray(r.bubble_area) ? r.bubble_area.map(x => x.toFixed(2)).join(', ') : (r.bubble_area ?? '')}</td><td>${Array.isArray(r.bubble_circularity) ? r.bubble_circularity.map(x => x.toFixed(2)).join(', ') : (r.bubble_circularity ?? '')}</td></tr>`;
                    });
                    html += `</tbody></table>`;

                    // Add rejected areas table if any exist
                    const rejectedAreas = [];
                    Object.entries(data.results).forEach(([questionKey, r]) => {
                        if (r.rejected_areas && Array.isArray(r.rejected_areas)) {
                            r.rejected_areas.forEach(area => {
                                rejectedAreas.push({
                                    question_number: questionKey.replace('question_', ''),
                                    circularity: area.circularity,
                                    area: area.area,
                                    reason: area.reason || 'Unknown'
                                });
                            });
                        }
                    });

                    if (rejectedAreas.length > 0) {
                        html += `
                            <div class="mt-4">
                                <h5>Rejected Areas Analysis</h5>
                                <table class='results-table'>
                                    <thead>
                                        <tr>
                                            <th>Question</th>
                                            <th>Circularity</th>
                                            <th>Area (pixels)</th>
                                            <th>Reason</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${rejectedAreas.map(area => `
                                            <tr>
                                                <td>${area.question_number}</td>
                                                <td>${Number(area.circularity).toFixed(2)}</td>
                                                <td>${Number(area.area).toFixed(2)}</td>
                                                <td>${area.reason}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>`;
                    }
                }
                if (data.combined_image) {
                    // Prefer /output/combined_questions.jpg endpoint for always-fresh image
                    const imgUrl = '/output/combined_questions.jpg?t=' + new Date().getTime();
                    html += `<div class='mt-4'><img src="${imgUrl}" class="img-fluid" alt="Combined Results"></div>`;
                }
                results.innerHTML = html;
            }
        })
        .catch(err => {
            loading.style.display = 'none';
            errorAlert.textContent = 'An error occurred while processing the image.';
            errorAlert.style.display = 'block';
        });
    });
});
