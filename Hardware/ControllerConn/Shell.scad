CUTAWAY_TOP = false;
CUTAWAY_SIDE = false;
MODEL = "D";
SHOW_PARTS = false;
TRANSFORM = 1;

BOARD_CLIP_DEPTH = 0.4;
BOARD_SIDE_TOL = 0.1;
BOARD_END_TOL = 0.1;
BOARD_THICK_TOL = 0.05;
EPSILON = 0.001;

module mirrcpy(axis) {
    children();
    mirror(axis) children();
}

module final_transform() {
    MODEL_LENGTH = (MODEL == "D") ? 15 : 20;
    MODEL_HEIGHT = (MODEL == "D") ? 3 : 2.4;
    if(TRANSFORM == 3) {
        rotate([90,0,0])
        children();
    } else if(TRANSFORM == 2) {
        rotate([-90,0,0])
        translate([0,-MODEL_LENGTH,0])
        children();
    } else if(TRANSFORM == 1) {
        translate([0,-MODEL_LENGTH/2,MODEL_HEIGHT])
        //rotate([0,180,0])
        children();
    } else children();
}

module gen_slice(t) {
    rotate([0,90,0])
    rotate([0,0,90])
    linear_extrude(t, center=true, convexity=10)
    mirrcpy([0,1,0]) children();
}

module slice_contact_a(t, f=0.4) {
    gen_slice(t)
    polygon([
        [0,2.4], [15,2.4], [15,1.6],
        [9,1.6], [9,0.8+f], [7,0.8+f],
        [7,1.6], [2,1.6], [2,0.8],
        [1,0.8], [0,1.3]
    ]);
}

module slice_between_a(t, f=0.4) {
    tt = BOARD_THICK_TOL;
    gen_slice(t)
    polygon([
        [0,2.4], [15,2.4], [15,1.6],
        [9,1.6], [9,0.8+f], [6,0.8+f],
        [6,0.8], [2,0.8], [1,0.8], [0,1.3]
    ]);
}

module slice_contact_bc(t) {
    st = 0;
    gen_slice(t) {
        // Front
        polygon([
            [0,2.4], [1.5,2.4], [1.5,2], [1.2,1.6],
            [1.2,0.8], [1,0.8], [0,1.3]
        ]);
        // Back
        polygon([
            [9,2.4], [15,2.4],
            [15,1.6], [9,1.6]
        ]);
    }
    gen_slice(t-2*st) {
        polygon([
            // Inner
            [9,1.6], [8,1.55], [7,1.4],
            [5,0.85], [4.5,0.75], [4,0.7],
            [3.5,0.7], [3,0.75], [2.4,0.9],
            [1.9,1.1],
            // Outer
            [1.9,1.5], [2.3,1.8], [4.3,1.8],
            [5,1.9], [7,2.3], [8,2.4], [9,2.4],
        ]);
    }
}

module slice_between_bc(t, f=0.15) {
    tt = BOARD_THICK_TOL;
    gen_slice(t) {
        // Front
        polygon([
            [0,2.4], [1.5,2.4], [1.5,2], [1.2,1.6],
            [1.2,0.8], [1,0.8], [0,1.3]
        ]);
        // Back
        polygon([
            [9,2.4], [15,2.4],
            [15,1.6], [9,1.6]
        ]);
    }
}

module end_abc(inner=5) {
    b = BOARD_CLIP_DEPTH;
    tt = BOARD_THICK_TOL;
    difference() {
        union() {
            linear_extrude(4, center=true, convexity=10)
            polygon([
                [9.5,1], [10,0], [11,0],
                [11,20], [10,20], [10-b,19.1],
                [10,19], [10,9], [9,9],
                [9,7], [10,6], [10,2],
                [9.5,2]
            ]);
            translate([(11+inner)/2,0,0])
            gen_slice(11-inner)
            polygon([
                [0,2.4], [20,2.4], [20,0.8+tt],
                [7,0.8+tt], [6,0.8],
                [1,0.8], [0,1.3]
            ]);
            translate([11-EPSILON,5,1])
            rotate([0,90,0])
            cylinder(h=0.5, r1=0.7, r2=0.2, $fn=16);
        }
        translate([10-0.1,-1,-2.4-0.1])
        rotate([0,45,0]) cube([2,10,2]);
    }
}

module slice_contact_d(t) {
    gen_slice(t) {
        // Middle
        polygon([
            [15.0,0.0], [15.0,0.3],
            [12.3,0.3], [11.4,0.6],
            [11.4,0.3], [10.6,0.3],
            [10.6,0.0]
        ]);
        // Outer
        polygon([
            [15.0,3.0], [8.5,3.0],
            [8.0,2.4], [0.0,2.4],
            [0.0,1.3], [1.0,0.8],
            [2.8,0.8], [2.2,1.3],
            [1.5,1.3], [1.0,1.7],
            [1.0,1.8], [8.0,1.8],
            [10.0,1.9], [15.0,1.9]
        ]);
    }
}

module slice_between_d(t) {
    gen_slice(t) {
        // Outer
        polygon([
            [15.0,3.0], [8.5,3.0],
            [8.0,2.4], [0.0,2.4],
            [0.0,1.3], [1.0,0.8],
            [7.0,0.8], [7.0,0.0],
            [15.0,0.0]
        ]);
    }
}

module end_d(inner=5) {
    difference() {
        union() {
            linear_extrude(4, center=true, convexity=10)
            polygon([
                [9.5,1.0], [10.0,0.0],
                [11.0,0.0], [11.0,15.0],
                [inner,15.0], [inner,7.0],
                [9.0,7.0], [9.8,6.0],
                [9.8,2.0], [9.5,2.0]
            ]);
            translate([(11+inner)/2,0,0])
            gen_slice(11-inner)
            polygon([
                [0.0,2.4], [8.0,2.4],
                [8.5,3.0], [15.0,3.0],
                [15.0,0.0], [7.0,0.0],
                [7.0,0.8], [1.0,0.8],
                [0.0,1.3]
            ]);
            translate([11-EPSILON,5,1])
            rotate([0,90,0])
            cylinder(h=0.5, r1=0.7, r2=0.2, $fn=16);
        }
        translate([10-0.1,-1,-2.4-0.1])
        rotate([0,45,0]) cube([2,9,2]);
    }
}

module shell() {
    difference() {
        union() mirrcpy([1,0,0]) {
            if(MODEL == "D") {
                for(m=[0,2,4,6,8]) translate([m,0,0])
                    slice_between_d(0.5);
                for(m=[1,3,5,7]) translate([m,0,0])
                    slice_contact_d(1.5+EPSILON);
                end_d(8.25-EPSILON);
            } else if(MODEL == "C") {
                translate([8,0,0])
                    slice_between_bc(1+EPSILON);
                slice_contact_bc(15.2);
                end_abc(8.5);
            } else if(MODEL == "B") {
                for(m=[0,2,4,6,8]) translate([m,0,0])
                    slice_between_bc(0.8+EPSILON);
                for(m=[1,3,5,7]) translate([m,0,0])
                    slice_contact_bc(1.2);
                end_abc(8.4);
            } else {
                for(m=[0,2,4,6,8]) translate([m,0,0])
                    slice_between_a(0.8+EPSILON);
                for(m=[1,3,5,7]) translate([m,0,0])
                    slice_contact_a(1.2);
                end_abc(8.4);
            }
        }
    }
}

module preview_parts() {
    b = BOARD_CLIP_DEPTH+0.4;
    t = BOARD_SIDE_TOL;
    te = BOARD_END_TOL;
    
    color("#AAAA55")
    mirrcpy([1,0,0]) difference() {
        linear_extrude(1.6, center=true, convexity=5)
        polygon([
            [0,7], [8.5,7], [8.5,9+te], [10-t,9+te],
            [10-t,19], [10-b,19], [10-b,20], [0,20]
        ]);
        hull() {
            translate([8.8,10.5,0])
            cylinder(2, d=0.9, center=true, $fn=16);
            translate([10,10.5,0])
            cylinder(2, d=0.9, center=true, $fn=16);
        }
    }
}

final_transform() {
    if($preview) difference() {
        shell();
        if(CUTAWAY_TOP) translate([-12,-1,0])
            cube([24,22,5]);
        if(CUTAWAY_SIDE) translate([-12,-1,-5])
            cube([12,22,10]);
    } else shell();
    if($preview && SHOW_PARTS) preview_parts();
}