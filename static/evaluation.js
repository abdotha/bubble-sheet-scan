// evaluation.js - Handles model answers upload, file upload, and evaluation result display for evaluation.html

document.addEventListener('DOMContentLoaded', function () {
    const modelAnswersForm = document.getElementById('modelAnswersForm');
    const numberOfQuestions = document.getElementById('numberOfQuestions');
    const modelAnswers = document.getElementById('modelAnswers');
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const selectedFile = document.getElementById('selectedFile');
    const errorAlert = document.getElementById('errorAlert');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const preview = document.getElementById('preview');
 
    // Handle model answers form
    modelAnswersForm.addEventListener('submit', function (e) {
        e.preventDefault();
        errorAlert.style.display = 'none';
        loading.style.display = 'block';
        results.innerHTML = '';

        const numQuestions = parseInt(numberOfQuestions.value, 10);
        const answers = modelAnswers.value.split(',').map(a => parseInt(a.trim(), 10));
        if (answers.length !== numQuestions || answers.some(isNaN)) {
            loading.style.display = 'none';
            errorAlert.textContent = 'Please enter the correct number of answers (comma-separated, numbers only).';
            errorAlert.style.display = 'block';
            return;
        }

        fetch('/upload_model_answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ number_of_questions: numQuestions, answers: answers })
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.error || data.detail) {
                errorAlert.textContent = data.error || data.detail;
                errorAlert.style.display = 'block';
            } else {
                results.innerHTML = `<div class='success-message'>Model answers saved successfully.</div>`;
            }
        })
        .catch(err => {
            loading.style.display = 'none';
            errorAlert.textContent = 'An error occurred while saving model answers.';
            errorAlert.style.display = 'block';
        });
    });

    // Handle file input preview
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

    // Handle bubble sheet upload for evaluation
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

        fetch('/evaluate', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.error || data.detail) {
                errorAlert.textContent = data.error || data.detail;
                errorAlert.style.display = 'block';
            } else if (data.evaluation_results) {
                let html = `<div class='summary-section'><div class='summary-title'>Evaluation Summary</div>`;
                html += `<div class='summary-grid'>`;
                html += `<div class='summary-item total'><h3>Total Questions</h3><div class='value'>${data.summary.total_questions}</div></div>`;
                html += `<div class='summary-item correct'><h3>Correct</h3><div class='value'>${data.summary.correct_answers}</div></div>`;
                html += `<div class='summary-item incorrect'><h3>Incorrect</h3><div class='value'>${data.summary.total_questions - data.summary.correct_answers}</div></div>`;
                html += `<div class='summary-item percentage'><h3>Score</h3><div class='value'>${data.summary.score.toFixed(2)}%</div></div>`;
                html += `</div></div>`;
                html += `<table class='results-table'><thead><tr><th>Q#</th><th>Your Answer</th><th>Correct</th><th>Status</th></tr></thead><tbody>`;
                data.evaluation_results.forEach(r => {
                    let status = r.is_correct ? 'Correct' : (r.has_multiple_answers ? 'Multiple' : 'Incorrect');
                    let rowClass = r.is_correct ? 'correct' : (r.has_multiple_answers ? 'warning' : 'incorrect');
                    html += `<tr class='${rowClass}'><td>${r.question}</td><td>${r.student_answer_display}</td><td>${r.correct_answer}</td><td>${status}</td></tr>`;
                });
                html += `</tbody></table>`;
                if (data.combined_image) {
                    // Add timestamp and random number to prevent caching
                    const timestamp = new Date().getTime();
                    const random = Math.random();
                    const imgUrl = `/output/combined_questions.jpg?t=${timestamp}&r=${random}`;
                    
                    // Create image element with loading handler
                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'mt-4';
                    
                    const img = document.createElement('img');
                    img.src = imgUrl;
                    img.className = 'img-fluid';
                    img.alt = 'Combined Results';
                    img.style.maxWidth = '100%';
                    
                    // Add error handling
                    img.onerror = function() {
                        console.error('Error loading combined image');
                        imgContainer.innerHTML = '<div class="alert alert-warning">Error loading combined image. Please try again.</div>';
                    };
                    
                    imgContainer.appendChild(img);
                    html += imgContainer.outerHTML;
                }
                results.innerHTML = html;
            }
        })
        .catch(err => {
            loading.style.display = 'none';
            errorAlert.textContent = 'An error occurred while evaluating the image.';
            errorAlert.style.display = 'block';
        });
    });
});
