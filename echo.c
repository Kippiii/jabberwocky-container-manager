#include <stdio.h>

int main(int argc, char const *argv[])
{
    char str[100];
    printf("Enter string: (Under 100 characters please): ");
    fflush(stdout);
    scanf("%s", str);
    printf("ECHO: %s\n", str);

    return 0;
}
