import turtle
from math import sqrt, tan, atan, degrees, pi, cos, sin
import sys

# KEYBIND GUIDE
# SIDE ARROWS: CHANGE LAUNCH ANGLE OR BACKBOARD POSITION
# P/DOWN ARROWS: CHANGE THE INCREMENT
# SPACEBAR: LAUNCH
# R: RESET
# S: SWITCH TO/FROM BACKBOARD ROTATION

# Ensure b > a
a = 250
b = 400
c = sqrt(b*b-a*a)

# Scale rim size. Radius and rim center coordinates.
SHOOTER_TO_RIM_IN_FEET = 23.75
r = 0.75 * 2*c/SHOOTER_TO_RIM_IN_FEET
rc = (0,c)
AIM_LINE_LENGTH = c/5

# Backboard Specs (6ft across, or 
BB_WIDTH = 8*r
BB_WIDTH_2 = (2/3)*r
bb_angle = 90
rotate_backboard = False
lines = []

# Shooter initial coordinates
shooter_coords = (0,-c)

# Conditions
STOP_PROXIMITY = 4*r
CHECK_PROXIMITY_AFTER_X_FEET = SHOOTER_TO_RIM_IN_FEET
IGNORE_RIM_AND_BACKBOARD_AFTER_X_FEET = 1.221 * SHOOTER_TO_RIM_IN_FEET  # 29 when three pointer
distance_tracker = 0

# Launching Specs
LAUNCH_SPEED = 6
rotation_size = 1

p = turtle.Turtle()
setup = turtle.Turtle()
bb_setup = turtle.Turtle()
redline = turtle.Turtle()

def main():
    # Set up the board
    redline.speed(0)
    setup.speed(0)
    bb_setup.speed(0)
    bb_setup.hideturtle()
    bb_setup.color("red")
    setup.hideturtle()
    redline.hideturtle()
    p.hideturtle()
    p.shape("circle")
    draw_ellipse()
    draw_rim()
    draw_backboard()
    goto_shooting_spot()
    p.showturtle()
    start_event_listeners()
    p.pendown()
    turtle.done()

# Ball moves until it has reflected back to the thrower
def launch():
    p.pencolor("green")
    p.speed(LAUNCH_SPEED)
    global distance_tracker
    distance_tracker = 0

    while True:
        ## Find all intersections
        intersections = []
        m = tan((pi/180)*p.heading())
        cur_x = p.xcor()
        cur_y = p.ycor()
        cur_heading = p.heading()

        # On elliptical border
        A = (b*b+a*a*m*m)
        B = (2*a*a*cur_y*m - 2*a*a*m*m*cur_x)
        C = (a*a*m*m*cur_x*cur_x - 2*a*a*cur_y*m*cur_x+a*a*cur_y*cur_y-a*a*b*b)
        for sign in [-1, 1]:
            i = (-B + sign*sqrt(B*B-4*A*C))/(2*A)
            j = m*(i-cur_x) + cur_y
            intersections.append((i,j,"e"))
        
        # On circular rim
        rim_intersections = line_circle_intersect(m, cur_x, cur_y, rc[0], rc[1], r)
        if rim_intersections:
            for intersect in rim_intersections:
                distance_to_intersect = (dist_btween((cur_x, cur_y),intersect) * SHOOTER_TO_RIM_IN_FEET / (2*c))
                if (distance_tracker + distance_to_intersect < IGNORE_RIM_AND_BACKBOARD_AFTER_X_FEET):
                    intersections.append((intersect[0], intersect[1], "r"))

        # On backboard
        for line in lines:
            mb = (line[0][1] - line[1][1])/(line[0][0] - line[1][0])
            intersect = line_line_intersect(m, cur_x, cur_y, mb, line[0][0], line[0][1])
            distance_to_intersect = (dist_btween((cur_x, cur_y),intersect) * SHOOTER_TO_RIM_IN_FEET / (2*c))
            # Ensure the intersection is on the restricted domain of the backboard lines
            # Check if the ball has travelled too far to hit the board
            if (((line[0][0] < line[1][0]) and (line[0][0] < intersect[0] < line[1][0])) or ((line[1][0] < line[0][0]) and (line[1][0] < intersect[0] < line[0][0]))) \
                and (distance_tracker + distance_to_intersect) < IGNORE_RIM_AND_BACKBOARD_AFTER_X_FEET:
                intersections.append((intersect[0], intersect[1], mb))

        ## Find which intersection point is your destination
        ## Stop simulation if ball ends up within the "stop proximity" of the shooter
        destination = find_destination(intersections, cur_y)
        output = proximity_check(destination, cur_x, cur_y, m)
        if output and distance_tracker > CHECK_PROXIMITY_AFTER_X_FEET:
            p.goto(output[0])
            print(f"The ball returned {(output[1] * SHOOTER_TO_RIM_IN_FEET / (2 * c)):.2f} feet away from the shooter.")
            break
        else:
            p.goto(destination[0], destination[1])
        # Track distance travelled. Convert to "feet".
        distance_tracker += (dist_btween((cur_x,cur_y),(destination[0],destination[1])) * SHOOTER_TO_RIM_IN_FEET / (2*c))

        ## Find slope of normal line
        # If collided with elliptical border
        if destination[2] == "e":
            derivative = ((-destination[1]/abs(destination[1]))*b*destination[0])/(a*a*sqrt(1-((destination[0]**2)/(a*a))))
            m_normal = -1 / derivative
        # If collided with circular rim
        elif destination[2] == "r":
            m_normal = (rc[1]-destination[1])/(rc[0]-destination[0])
        # If collided with piece of backboard
        else:
            m_normal = -1/destination[2]

        ## Find new heading
        # Alpha is the +/- angle from the horizontal to the normal line
        # Beta is the +/- angle from the horizontal to the current path
        alpha = atan(m_normal)
        beta = atan(m)
        beta_prime = beta - (beta/abs(beta))*pi
        if abs(alpha - B) > (pi/2):
            angle_of_incidence = alpha - beta_prime
        else:
            angle_of_incidence = alpha - beta
        new_heading = clean_angle((cur_heading + 2 * ((180/pi) * angle_of_incidence)) - 180)
        p.setheading(new_heading)
        print(f"New heading: {new_heading}")
    
# Finds the right destination out of the set of possibilites on the current path.
def find_destination(intersections, cur_y):
    to_remove = []
    if p.heading() == 0 or p.heading() == 180 or p.heading() == 360:
        print("Heading sideways!")
        sys.exit(1)
    for point in intersections:
        if ((0 < p.heading() < 180) and (point[1] < cur_y or near_equal(point[1], cur_y))) or ((180 < p.heading() < 360) and (point[1] > cur_y or near_equal(point[1], cur_y))):
            to_remove.append(point)
    for point in to_remove:
        intersections.remove(point)
    destination = intersections[0]
    for point in intersections:
        if ((0 < p.heading() < 180) and (point[1] < destination[1])) or ((180 < p.heading() < 360) and (point[1] > destination[1])):
            destination = point
    return destination

# Does the ball reach critical proximity to shooter on its current path?
def proximity_check(destination, cur_x, cur_y, m):

    # If the ball reaches the stop proximity, then it will reach the minimum distance

    # Find set of x_values in which the ball is within the stop proximity to the shooter, if this set exists.
    ints = line_circle_intersect(m, cur_x, cur_y, shooter_coords[0], shooter_coords[1], STOP_PROXIMITY)
    if ints:
        if ints[0][0] < ints[1][0]:
            pdmin = ints[0][0]
            pdmax = ints[1][0]
        else:
            pdmin = ints[1][0]
            pdmax = ints[0][0]
    else:
        return None

    # Find the set of x_values through which the ball will travel on its current path.
    if cur_x < destination[0]:
        tdmin = cur_x
        tdmax = destination[0]
    else:
        tdmin = destination[0]
        tdmax = cur_x

    # Check if these sets intersect.
    # Assuming the ball eventually reaches the "stop proximity" circle, the "stop proximity" x-values will be nested in the trajectory x-values.
    # Ie: the starting point and destination will be outside the "stop proximity", so we just need to check if the "stop proximity" x-values are nested in the trajectory.
    # If these domains intersect, the ball will reach the absolute minimum distance from the shooter on its curent path. This absolute minimum is easily calculated.

    if pdmin >= tdmin and pdmax <= tdmax:
        min_x = (pdmin + pdmax) / 2
        min_y = m*(min_x - cur_x) + cur_y
        proximity = sqrt((min_x - shooter_coords[0])**2 + (min_y - shooter_coords[1])**2)
        return [(min_x,min_y), proximity]
    else:
        return None

def draw_ellipse():
    for sign in [-1, 1]:
        setup.penup()
        setup.goto(-a,E(-a))
        setup.pendown()
        for x in range(-a, a+1, 2):
            setup.goto(x, sign * E(x))

def draw_rim():
    setup.penup()
    setup.pencolor("red")
    setup.goto(rc[0],rc[1]-r)
    setup.pendown()
    setup.circle(r)

def draw_backboard():

    lines.clear()
    # tan90 is too large
    global bb_angle
    if bb_angle == 90:
        bb_angle = 90.0001

    # Line in slope point form
    bb_angle_rad = (pi/180) * bb_angle
    x1 = rc[0] + (5/3)*r*cos(bb_angle_rad)
    y1 = rc[1] + (5/3)*r*sin(bb_angle_rad)
    mb = -1 / tan(bb_angle_rad)

    # Find edge coordinates based on known width of backboard
    min_x = x1 - (BB_WIDTH/2)*cos((pi/2) - bb_angle_rad)
    max_x = x1 + (BB_WIDTH/2)*cos((pi/2) - bb_angle_rad)
    left_edge = (min_x, mb*(min_x - x1) + y1)
    right_edge = (max_x, mb*(max_x - x1) + y1)
    lines.append((left_edge,right_edge))

    # Setup rim support bars
    ms = -1/mb
    for sign in [-1, 1]:
        x2 = x1 + sign*(BB_WIDTH_2/2)*cos((pi/2)-bb_angle_rad)
        y2 = mb*(x2 - x1) + y1
        ints = line_circle_intersect(ms, x2, y2, rc[0], rc[1], r)
        if dist_btween((x2,y2), ints[0]) < dist_btween((x2,y2), ints[1]):
            lines.append(((x2,y2), ints[0]))
        else:
            lines.append(((x2,y2), ints[1]))
    
    # Draw all three lines
    bb_setup.clear()
    for line in lines:
        bb_setup.penup()
        bb_setup.goto(line[0])
        bb_setup.pendown()
        bb_setup.goto(line[1])
        bb_setup.penup()

def goto_shooting_spot():
    redline.clear()
    p.speed(0)
    redline.penup()
    p.penup()
    redline.goto(shooter_coords)
    p.goto(shooter_coords)
    redline.setheading(90)
    p.setheading(90)
    redline.pendown()
    p.pendown()
    redline.pencolor("red")
    p.pencolor("green")
    redline.forward(AIM_LINE_LENGTH)
    redline.goto(shooter_coords)

def start_event_listeners():
    s = turtle.Screen()
    s.listen()
    s.onkey(rotation_size_up, "Up")
    s.onkey(rotation_size_down, "Down")
    s.onkey(rotate_left, "Left")
    s.onkey(rotate_right, "Right")
    s.onkey(launch, "space")
    s.onkey(reset, "r")
    s.onkey(toggle_rotation, "s")
    p.color("orange")

def rotate_left():
    global bb_angle
    if rotate_backboard:
        bb_angle += rotation_size
        print(f"Backboard Angle: {bb_angle}")
        draw_backboard()
    else:
        redline.clear()
        p.left(rotation_size)
        redline.left(rotation_size)
        redline.forward(AIM_LINE_LENGTH)
        redline.goto(shooter_coords)
        print(f"Heading: {p.heading()}")

def rotate_right():
    global bb_angle
    if rotate_backboard:
        bb_angle -= rotation_size
        print(f"Backboard Angle: {bb_angle}")
        draw_backboard()
    else:
        redline.clear()
        p.right(rotation_size)
        redline.right(rotation_size)
        redline.forward(AIM_LINE_LENGTH)
        redline.goto(shooter_coords)
        print(f"Heading: {p.heading()}")

def rotation_size_up():
    global rotation_size
    rotation_size *= 10
    print(f"New Rotation Size: {rotation_size} degrees")

def rotation_size_down():
    global rotation_size
    rotation_size /= 10
    print(f"New Rotation Size: {rotation_size} degrees")
    

# Returns top-half ellipse y-value for a given x-value
def E(x):
    return b*sqrt(1-(x*x)/(a*a))

# Find equivalent angle within [0, 360]
def clean_angle(angle):
    while angle < 0:
        angle += 360
    while angle > 360:
        angle -= 360
    return angle

# Checks if two numbers are less than 0.001 apart. Accounts for slight inaccuracies when comparing floats.
def near_equal(i, j):
    if abs(i - j) < 0.01:
        return True
    else:
        return False
    
def reset():
    p.clear()
    goto_shooting_spot()

def toggle_rotation():
    global rotate_backboard
    if rotate_backboard:
        rotate_backboard = False
        print(f"Chosing Launch Angle")
    else:
        rotate_backboard = True
        print(f"Rotating Backboard")

# Returns points of intersection on given line and circle
def line_circle_intersect(m, x1, y1, h, k, r):
    intersections = []
    A = 1 + m*m
    B = 2*m*y1 - 2*h - 2*m*m*x1 - 2*m*k
    C = h*h + m*m*x1*x1 - 2*m*x1*y1 + 2*m*x1*k - 2*y1*k + y1*y1 + k*k - r*r
    try:
        for sign in [-1,1]:
            i = (-B + sign*sqrt(B*B - 4*A*C)) / (2*A)
            j = m*(i - x1) + y1
            intersections.append((i,j))
    except ValueError:
        return None
    return intersections

# Returns distance between two points
def dist_btween(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# Returns intersection of two lines
def line_line_intersect(m, x, y, m2, x2, y2):
    try:
        i = (m2*x2 - y2 - m*x + y) / (m2 - m)
        j = m*(i - x) + y
        return (i,j)
    except ValueError:
        return None
    
main()