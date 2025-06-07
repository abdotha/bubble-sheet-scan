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
            if (data.error) {
                errorAlert.textContent = data.error;
                errorAlert.style.display = 'block';
            } else {
                let html = '';
                if (data.results) {
                    // Build a table similar to evaluation.js
                    html += `<table class='results-table'><thead><tr><th>Q#</th><th>Detected Answer(s)</th><th>Bubbles Detected</th><th>Fill Ratios</th></tr></thead><tbody>`;
                    Object.keys(data.results).sort((a, b) => {
                        // Sort by question number
                        const numA = parseInt(a.replace('question_', ''));
                        const numB = parseInt(b.replace('question_', ''));
                        return numA - numB;
                    }).forEach(key => {
                        const r = data.results[key];
                        html += `<tr><td>${key.replace('question_', '')}</td><td>${Array.isArray(r.answer) ? r.answer.join(', ') : (r.answer ?? 'No Answer')}</td><td>${r.bubbles_detected ?? ''}</td><td>${Array.isArray(r.fill_ratios) ? r.fill_ratios.map(x => x.toFixed(2)).join(', ') : ''}</td></tr>`;
                    });
                    html += `</tbody></table>`;
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
