/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
    colors: {
        primary: {
            '50': 'hsl(0, 100%, 97%)',
            '100': 'hsl(0, 100%, 94%)',
            '200': 'hsl(0, 100%, 86%)',
            '300': 'hsl(0, 100%, 76%)',
            '400': 'hsl(0, 100%, 64%)',
            '500': 'hsl(0, 100%, 50%)',
            '600': 'hsl(0, 100%, 40%)',
            '700': 'hsl(0, 100%, 32%)',
            '800': 'hsl(0, 100%, 24%)',
            '900': 'hsl(0, 100%, 16%)',
            '950': 'hsl(0, 100%, 10%)',
            DEFAULT: '#ec0000'
        },
        secondary: {
            '50': 'hsl(27, 70%, 97%)',
            '100': 'hsl(27, 70%, 94%)',
            '200': 'hsl(27, 70%, 86%)',
            '300': 'hsl(27, 70%, 76%)',
            '400': 'hsl(27, 70%, 64%)',
            '500': 'hsl(27, 70%, 50%)',
            '600': 'hsl(27, 70%, 40%)',
            '700': 'hsl(27, 70%, 32%)',
            '800': 'hsl(27, 70%, 24%)',
            '900': 'hsl(27, 70%, 16%)',
            '950': 'hsl(27, 70%, 10%)',
            DEFAULT: '#d97a2b'
        },
        accent: {
            '50': 'hsl(42, 77%, 97%)',
            '100': 'hsl(42, 77%, 94%)',
            '200': 'hsl(42, 77%, 86%)',
            '300': 'hsl(42, 77%, 76%)',
            '400': 'hsl(42, 77%, 64%)',
            '500': 'hsl(42, 77%, 50%)',
            '600': 'hsl(42, 77%, 40%)',
            '700': 'hsl(42, 77%, 32%)',
            '800': 'hsl(42, 77%, 24%)',
            '900': 'hsl(42, 77%, 16%)',
            '950': 'hsl(42, 77%, 10%)',
            DEFAULT: '#e5b13a'
        },
        'neutral-50': '#000000',
        'neutral-100': '#5d6266',
        'neutral-200': '#ffffff',
        background: '#e4e8ea',
        foreground: '#000000'
    },
    fontFamily: {
        sans: [
            'Schibsted Grotesk',
            'sans-serif'
        ]
    },
    fontSize: {
        '12': [
            '12px',
            {
                lineHeight: '18px'
            }
        ],
        '13': [
            '13px',
            {
                lineHeight: '19.5px'
            }
        ],
        '14': [
            '14px',
            {
                lineHeight: '21px'
            }
        ],
        '15': [
            '15px',
            {
                lineHeight: '22.5px'
            }
        ],
        '18': [
            '18px',
            {
                lineHeight: '27px'
            }
        ],
        '26': [
            '26px',
            {
                lineHeight: '39px',
                letterSpacing: '-0.52px'
            }
        ],
        '56': [
            '56px',
            {
                lineHeight: '50.4px',
                letterSpacing: '-1.96px'
            }
        ],
        '64': [
            '64px',
            {
                lineHeight: '54.4px',
                letterSpacing: '-2.56px'
            }
        ],
        '8.69565': [
            '8.69565px',
            {
                lineHeight: '8.69565px',
                letterSpacing: '1.21739px'
            }
        ]
    },
    spacing: {
        '3': '6px',
        '6': '12px',
        '7': '14px',
        '8': '16px',
        '9': '18px',
        '11': '22px',
        '13': '26px',
        '14': '28px',
        '1px': '1px',
        '31px': '31px'
    },
    borderRadius: {
        xs: '2px',
        md: '10px',
        full: '999px'
    },
    boxShadow: {
        xs: 'rgb(207, 213, 216) 0px 1px 0px 0px',
        sm: 'rgba(30, 40, 50, 0.16) 0px 8px 28px 0px',
        md: 'rgba(30, 40, 50, 0.25) 0px 20px 60px 0px'
    }
},
  },
};
