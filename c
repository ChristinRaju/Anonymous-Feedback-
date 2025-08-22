#include <stdio.h>

void convertCurrency(float amount, float conversionRate) {
    printf("Converted Amount: %.2f\n", amount * conversionRate);
}

int main() {
    int choice;
    float amount;

    printf("Welcome to the Currency Converter!\n");
    printf("Select the currency you want to convert:\n");
    printf("1. USD to INR\n");
    printf("2. EUR to USD\n");
    printf("3. GBP to INR\n");
    printf("4. USD to EUR\n");
    printf("5. INR to GBP\n");
    printf("6. Exit\n");

    while (1) {
        printf("\nEnter your choice (1-6): ");
        scanf("%d", &choice);

        if (choice == 6) {
            printf("Exiting the Currency Converter...\n");
            break;
        }

        if (choice < 1 || choice > 6) {
            printf("Invalid choice! Please enter a valid option.\n");
            continue;
        }

        printf("Enter the amount to convert: ");
        scanf("%f", &amount);

        switch (choice) {
            case 1:  // USD to INR
                convertCurrency(amount, 82.71); 
                break;
            case 2:  // EUR to USD
                convertCurrency(amount, 1.07); 
                break;
            case 3:  // GBP to INR
                convertCurrency(amount, 101.58);  
                break;
            case 4:  // USD to EUR
                convertCurrency(amount, 0.94);  
                break;
            case 5:  // INR to GBP
                convertCurrency(amount, 0.0085); 
                break;
            default:
                printf("Invalid choice! Please try again.\n");
        }
    }

    return 0;
}