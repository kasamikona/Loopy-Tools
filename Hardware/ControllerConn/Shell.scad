CUTAWAY_TOP = true;
CUTAWAY_SIDE = false;
MODEL = "B";
SHOW_PARTS = true;
TRANSFORM = 0;

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
    if(TRANSFORM == 3) {
        rotate([90,0,0])
        children();
    } else if(TRANSFORM == 2) {
        rotate([-90,0,0])
        translate([0,-20,0])
        children();
    } else if(TRANSFORM == 1) {
        translate([0,-10,2.4])
        rotate([0,180,0])
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

module slice_contact_b(t, f=0.15) {
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

module slice_between_b(t, f=0.15) {
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

module end(inner=5) {
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
            translate([11,5,1.2])
            rotate([0,90,0])
            cylinder(h=0.2, r1=0.45, r2=0.2, $fn=16);
        }
        translate([10-0.1,-1,-2.4-0.1])
        rotate([0,45,0]) cube([2,10,2]);
    }
}

module shell() {
    difference() {
        union() mirrcpy([1,0,0]) {
            if(MODEL == "C") {
                translate([8,0,0])
                    slice_between_b(1+EPSILON);
                slice_contact_b(15.2);
                end(8.5);
            } else if(MODEL == "B") {
                for(m=[0,2,4,6,8]) translate([m,0,0])
                    slice_between_b(0.8+EPSILON);
                for(m=[1,3,5,7]) translate([m,0,0])
                    slice_contact_b(1.2);
                end(8.4);
            } else {
                for(m=[0,2,4,6,8]) translate([m,0,0])
                    slice_between_a(0.8+EPSILON);
                for(m=[1,3,5,7]) translate([m,0,0])
                    slice_contact_a(1.2);
                end(8.4);
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
            cube([24,22,2.5]);
        if(CUTAWAY_SIDE) translate([-12,-1,-2.5])
            cube([12,22,5]);
    } else shell();
    if($preview && SHOW_PARTS) preview_parts();
}