document.addEventListener('DOMContentLoaded', () => {
    const ratingInputs = document.querySelectorAll('input[name="rating"]');
    
    ratingInputs.forEach(input => {
        input.addEventListener('change', () => {
            const selectedRating = input.value;
            alert(`You have rated ${selectedRating} stars successfully!`);
        });
    });
});
