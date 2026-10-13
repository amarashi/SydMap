// React Theme — extracted from https://stop-token.com/lab/amsterdam/
// Compatible with: Chakra UI, Stitches, Vanilla Extract, or any CSS-in-JS

/**
 * TypeScript type definition for this theme:
 *
 * interface Theme {
 *   colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    foreground: string;
    neutral50: string;
    neutral100: string;
    neutral200: string;
 *   };
 *   fonts: {
    body: string;
 *   };
 *   fontSizes: {
    '12': string;
    '13': string;
    '14': string;
    '15': string;
    '18': string;
    '26': string;
    '56': string;
    '64': string;
    '8.69565': string;
 *   };
 *   space: {
    '1': string;
    '6': string;
    '12': string;
    '14': string;
    '16': string;
    '18': string;
    '22': string;
    '26': string;
    '28': string;
    '31': string;
 *   };
 *   radii: {
    xs: string;
    md: string;
    full: string;
 *   };
 *   shadows: {
    xs: string;
    xl: string;
 *   };
 *   states: {
 *     hover: { opacity: number };
 *     focus: { opacity: number };
 *     active: { opacity: number };
 *     disabled: { opacity: number };
 *   };
 * }
 */

export const theme = {
  "colors": {
    "primary": "#ec0000",
    "secondary": "#d97a2b",
    "accent": "#e5b13a",
    "background": "#e4e8ea",
    "foreground": "#000000",
    "neutral50": "#000000",
    "neutral100": "#5d6266",
    "neutral200": "#ffffff"
  },
  "fonts": {
    "body": "'Schibsted Grotesk', sans-serif"
  },
  "fontSizes": {
    "12": "12px",
    "13": "13px",
    "14": "14px",
    "15": "15px",
    "18": "18px",
    "26": "26px",
    "56": "56px",
    "64": "64px",
    "8.69565": "8.69565px"
  },
  "space": {
    "1": "1px",
    "6": "6px",
    "12": "12px",
    "14": "14px",
    "16": "16px",
    "18": "18px",
    "22": "22px",
    "26": "26px",
    "28": "28px",
    "31": "31px"
  },
  "radii": {
    "xs": "2px",
    "md": "10px",
    "full": "999px"
  },
  "shadows": {
    "xs": "rgb(207, 213, 216) 0px 1px 0px 0px",
    "xl": "rgba(30, 40, 50, 0.25) 0px 20px 60px 0px"
  },
  "states": {
    "hover": {
      "opacity": 0.08
    },
    "focus": {
      "opacity": 0.12
    },
    "active": {
      "opacity": 0.16
    },
    "disabled": {
      "opacity": 0.38
    }
  }
};

// MUI v5 theme
export const muiTheme = {
  "palette": {
    "primary": {
      "main": "#ec0000",
      "light": "hsl(0, 100%, 61%)",
      "dark": "hsl(0, 100%, 31%)"
    },
    "secondary": {
      "main": "#d97a2b",
      "light": "hsl(27, 70%, 66%)",
      "dark": "hsl(27, 70%, 36%)"
    },
    "background": {
      "default": "#e4e8ea",
      "paper": "#ffffff"
    },
    "text": {
      "primary": "#000000",
      "secondary": "#ffffff"
    }
  },
  "typography": {
    "fontFamily": "'Schibsted Grotesk', sans-serif",
    "h1": {
      "fontSize": "56px",
      "fontWeight": "800",
      "lineHeight": "50.4px"
    },
    "h2": {
      "fontSize": "26px",
      "fontWeight": "800",
      "lineHeight": "39px"
    },
    "body1": {
      "fontSize": "18px",
      "fontWeight": "400",
      "lineHeight": "27px"
    },
    "body2": {
      "fontSize": "14px",
      "fontWeight": "400",
      "lineHeight": "21px"
    }
  },
  "shape": {
    "borderRadius": 10
  },
  "shadows": [
    "rgb(207, 213, 216) 0px 1px 0px 0px",
    "rgba(30, 40, 50, 0.16) 0px 8px 28px 0px",
    "rgba(30, 40, 50, 0.2) 0px 10px 34px 0px",
    "rgba(30, 40, 50, 0.25) 0px 20px 60px 0px"
  ]
};

export default theme;
