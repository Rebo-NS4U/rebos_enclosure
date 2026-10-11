import Quickshell
pragma Singleton

Singleton {
    function getStyledRectConfig(v) {
        return {
            "gradient": [],
            "gradientType": "none",
            "gradientAngle": 0,
            "gradientCenterX": 0,
            "gradientCenterY": 0,
            "halftoneDotMin": 0,
            "halftoneDotMax": 0,
            "halftoneStart": 0,
            "halftoneEnd": 0,
            "color": "#333333",
            "itemColor": "#eeeeee",
            "opacity": 1
        };
    }

    function radius(n) {
        return n;
    }

    function fontSize(n) {
        return 14 + n;
    }

    function srItem(n) {
        return "#eeeeee";
    }

}
