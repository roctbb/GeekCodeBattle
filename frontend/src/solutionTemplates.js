export const CPP_TEMPLATE = `#include <iostream>

using namespace std;

int main() {
    // Ваш код здесь

    return 0;
}
`

export const defaultSourceCode = (language) => language === 'cpp' ? CPP_TEMPLATE : 'print("hello")'
