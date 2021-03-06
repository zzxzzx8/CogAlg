import cv2
import argparse
from time import time
from collections import deque

''' frame() is my core algorithm of levels 1 + 2, modified for 2D: segmentation of image into blobs, then search within and between blobs.
    frame_blobs() is frame() limited to definition of initial blobs per each of 4 derivatives, vs. per 2 gradients in current frame().

    In my code, Le denotes level of encoding, 
    prefix '_' denotes higher-line variable or pattern, vs. same-type lower-line variable or pattern,
    postfix '_' denotes array name, vs. same-name elements of that array,
    y per line below is shown as relative to y of current line, which is incremented with top-down input within a frame
    
    frame_blobs() performs several steps of encoding, incremental per scan line defined by vertical coordinate y:

    1Le, line y:    x_comp(p_): lateral pixel comparison -> tuple t ) array t_
    2Le, line y- 1: y_comp(t_): vertical pixel comp -> 2D tuple t2 ) array t2_ 
    3Le, line y- 1+ rng: form_P(t2) -> 1D pattern P ) P_  
    4Le, line y- 2+ rng: scan_P_(P, _P) -> _P, fork_, root_: downward and upward connections between Ps of adjacent lines 
    5Le, line y- 3+ rng: form_blob(_P, blob) -> blob: merge connected Ps into non-forking blob segments
    6Le, line y- 4+ rng+ + blob depth: term_blob, form_net -> net: merge connected segments into network of terminated forks
    
    These functions are tested through form_P, I am currently debugging scan_P_. 
    All 2D functions (ycomp, scan_P_, etc.) input two lines: higher and lower, convert elements of lower line 
    into elements of new higher line, and displace elements of old higher line into some higher function.
    Higher-line elements include additional variables, derived while they were lower-line elements.
    
    Pixel comparison in 2D forms lateral and vertical derivatives: 2 matches and 2 differences per pixel. 
    They are formed on the same level because average lateral match ~ average vertical match.
    Each vertical and horizontal derivative forms separate blobs, suppressing overlapping orthogonal representations.
    They can also be summed to estimate diagonal or hypot derivatives, for blob orientation to maximize primary derivatives.
    Orientation increases primary dimension of blob to maximize match, and decreases secondary dimension to maximize difference.
'''

def lateral_comp(p_):  # comparison over x coordinate: between min_rng of consecutive pixels within each line

    t_ = []  # complete tuples: summation range = rng
    rng_t_ = deque(maxlen=rng)  # array of tuples within rng of current pixel: summation range < rng
    max_index = rng - 1  # max index of rng_t_
    pri_d, pri_m = 0, 0  # fuzzy derivatives in prior completed tuple

    for p in p_:  # pixel p is compared to rng of prior pixels within horizontal line, summing d and m per prior pixel:
        for index, (pri_p, d, m) in enumerate(rng_t_):

            d += p - pri_p  # fuzzy d: running sum of differences between pixel and all subsequent pixels within rng
            m += min(p, pri_p)  # fuzzy m: running sum of matches between pixel and all subsequent pixels within rng

            if index < max_index:
                rng_t_[index] = (pri_p, d, m)
            else:
                t_.append((pri_p, d + pri_d, m + pri_m))  # completed bilateral tuple is transferred from rng_t_ to t_
                pri_d = d; pri_m = m  # to complement derivatives of next rng_t_: derived from next rng of pixels

        rng_t_.appendleft((p, 0, 0))  # new tuple with initialized d and m, maxlen displaces completed tuple from rng_t_

    t_ += reversed(rng_t_)  # or tuples of last rng (incomplete, in reverse order) are discarded?
    return t_


def vertical_comp(t_, t2__, _dP_, _vP_, _dyP_, _vyP_, dblob_, vblob_, dyblob_, vyblob_, dframe, vframe, dyframe, vyframe):

    # comparison between rng vertically consecutive pixels, forming t2: 2D tuple of derivatives per pixel

    dP  = 0,0,0,0,0,0,0,0,0,[]  # lateral difference pattern = pri_s, I, D, Dy, V, Vy, alt_der, alt_dir, alt_both, t2_
    vP  = 0,0,0,0,0,0,0,0,0,[]  # lateral value pattern;  same vars for all P types, initialized per line
    dyP = 0,0,0,0,0,0,0,0,0,[]  # vertical difference pattern
    vyP = 0,0,0,0,0,0,0,0,0,[]  # vertical value pattern

    dP_, vP_, dyP_, vyP_ = deque(),deque(),deque(),deque()  # line y - 1+ rng2
    dbuff_, vbuff_, dybuff_, vybuff_ = deque(),deque(),deque(),deque()  # line y- 2+ rng2: _Ps buffered by previous run of scan_P_
    new_t2__ = deque()  # 2D: line of t2_s buffered for next-line comp

    x = 0  # lateral coordinate of current pixel
    max_index = rng - 1  # max t2_ index
    min_coord = rng * 2 - 1  # min x and y for form_P input
    dy, my = 0, 0  # for initial rng of lines, to reload _dy, _vy = 0, 0 in higher tuple

    for (p, d, m), (t2_, _dy, _my) in zip(t_, t2__):  # pixel p is compared to rng of higher pixels in t2_, summing dy and my per higher pixel:
        x += 1
        index = 0

        for (_p, _d, _m, dy, my) in t2_:  # 2D tuples are vertically incomplete; prefix '_' denotes higher-line variable

            dy += p - _p   # fuzzy dy: running sum of differences between pixel and all lower pixels within rng
            my += min(p, _p)  # fuzzy my: running sum of matches between pixel and all lower pixels within rng

            if index < max_index:
                t2_[index] = (_p, d, m, dy, my)

            elif x > min_coord and y > min_coord:  # or min y is increased by x_comp on line y=0?
                _v = _m - ave
                vy = my + _my - ave
                t2 = _p, _d, _v, dy + _dy, vy  # completed bilateral 2D tuples are inputted to form_P (pattern):

                # forms 1D patterns vP, vPy, dP, dPy: horizontal spans of same-sign core derivative:

                dP,  dP_,  dbuff_,  _dP_,  dblob_,  dframe = form_P(0, t2, x, dP,  dP_,  dbuff_,  _dP_,  dblob_, dframe)
                vP,  vP_,  vbuff_,  _vP_,  vblob_,  vframe = form_P(1, t2, x, vP,  vP_,  vbuff_,  _vP_,  vblob_, vframe)
                dyP, dyP_, dybuff_, _dyP_, dyblob_, dyframe= form_P(2, t2, x, dyP, dyP_, dybuff_, _dyP_, dyblob_, dyframe)
                vyP, vyP_, vybuff_, _vyP_, vyblob_, vyframe= form_P(3, t2, x, vyP, vyP_, vybuff_, _vyP_, vyblob_, vyframe)

            index += 1

        t2_.appendleft((p, d, m, 0, 0))  # initial dy and my = 0, new t2 replaces completed t2 in vertical t2_ via maxlen
        new_t2__.append((t2_, dy, my))  # vertically-incomplete 2D array of tuples, converted to t2__, for next-line ycomp

    # line ends, current patterns are sent to scan_P_, t2s with incomplete lateral fd and fm are discarded?
    # if y > rng2 + 2:  # starting with the first returned _P_: vertical interconnection of laterally marginal patterns:

      #  dP_, dbuff_, _dP_, dblob_, dframe = scan_P_(0, x, dP, dP_, dbuff_, _dP_, dblob_, dframe)  # returns empty _dP_
      #  vP_, vbuff_, _vP_, vblob_, vframe = scan_P_(1, x, vP, vP_, vbuff_, _vP_, vblob_, vframe)  # returns empty _vP_
      #  dyP_, dybuff_, _dyP_, dyblob_, dyframe = scan_P_(3, x, dyP, dybuff_, dyP_, _dyP_, dyblob_, dyframe)  # returns empty _dyP_
      #  vyP_, vybuff_, _vyP_, vyblob_, vyframe = scan_P_(4, x, vyP, vybuff_, vyP_, _vyP_, vyblob_, vyframe)  # returns empty _vyP_

    # last vertical rng of lines (vertically incomplete t2__) is discarded,
    # but scan_P_ inputs vertically incomplete patterns, to be added to image_to_blobs() at y = Y-1

    return new_t2__, dP_, vP_, dyP_, vyP_, dblob_, vblob_, dyblob_, vyblob_, dframe, vframe, dyframe, vyframe  # extended in scan_P_


def form_P(typ, t2, x, P, P_, buff_, _P_, blob_, frame):  # terminates, initializes, accumulates 1D pattern: dP | vP | dyP | vyP

    p, d, v, dy, vy = t2  # 2D tuple of derivatives per pixel, "y" for vertical dimension:

    if   typ == 0: core = d; alt_der = v; alt_dir = dy; alt_both = vy  # core: variable that defines current type of pattern,
    elif typ == 1: core = v; alt_der = d; alt_dir = vy; alt_both = dy  # alt cores define overlapping alternative-type patterns:
    elif typ == 2: core = dy; alt_der = vy; alt_dir = d; alt_both = v  # alt derivative, alt direction, alt derivative_and_direction
    else:          core = vy; alt_der = dy; alt_dir = v; alt_both = d

    s = 1 if core > 0 else 0  # core = 0 is negative: no selection?

    if s == P[0] or x == rng*2:  # s == pri_s or initialized pri_s: P is continued, else terminated:
        pri_s, I, D, Dy, V, Vy, alt_Der, alt_Dir, alt_Both, t2_ = P
    else:
        if y == rng*2:  # first line of Ps, _P_ is empty till vertical comp returns P_:
            P_.append((P, x-1, []))  # empty _fork_ in the first line of _Ps, x-1 for delayed P displacement
        else:
            P_, buff_, _P_, blob_, frame = scan_P_(typ, x-1, P, P_, buff_, _P_, blob_, frame)  # scans higher-line Ps for contiguity
        I, D, Dy, V, Vy, alt_Der, alt_Dir, alt_Both, t2_ = 0,0,0,0,0,0,0,0,[]  # new P initialization

    I += p  # summed input and derivatives are accumulated as P and alt_P parameters, continued or initialized:
    D += d    # lateral D
    Dy += dy  # vertical D
    V += v    # lateral V
    Vy += vy  # vertical V
    alt_Der += abs(alt_der)  # abs alt cores indicate value of alt-core Ps, to compute P redundancy rate
    alt_Dir += abs(alt_dir)  # vs. specific overlaps: cost > gain in precision?
    alt_Both+= abs(alt_both)
    t2_.append(t2)  # t2s are buffered for oriented rescan and incremental range | derivation comp

    P = s, I, D, Dy, V, Vy, alt_Der, alt_Dir, alt_Both, t2_
    return P, P_, buff_, _P_, blob_, frame  # accumulated within line


def scan_P_(typ, x, P, P_, _buff_, _P_, blob_, frame):  # P scans shared-x-coordinate _Ps in _P_, forms overlaps

    buff_ = deque()  # new buffer for displaced _Ps, for scan_P_(next P)
    fork_ = []  # _Ps connected to input P
    ix = x - len(P[9])  # initial x coordinate of P( pri_s, I, D, Dy, V, Vy, alt_der, alt_dir, alt_both, t2_)
    _ix = 0  # initial x coordinate of _P

    while _ix <= x:  # while horizontal overlap between P and _P, then P -> P_
        if _buff_:
            _P, _x, _fork_, roots, oLen, oCore = _buff_.popleft()  # _Ps buffered in prior run of scan_P_
        elif _P_:
            _P, _x, _fork_ = _P_.popleft()  # _P: y-2, _root_: y-3, contains blobs that replace _Ps
            oLen, oCore = 0, 0  # length of and core summed over vertical overlap between Ps and _P
            roots = 0  # count of Ps connected to current _P
        else:
            break  # higher line ends

        _ix = _x - len(_P[9])  # len(t2_)
        if P[0] == _P[0]:  # if s == _s (core sign match):

            t2_x = x  # x coordinate of t2 loaded to compute vertical overlap | contiguity between P and _P:
            olen, ocore = 0,0
            while t2_x > _ix:
                for (t2) in reversed(P[9]):  # t2_ reversal for core only, t2 = p, d, v, dy, vy:
                    if   typ == 0: ocore += t2[1]
                    elif typ == 1: ocore += t2[2]  # core is summed within overlap for blob contiguity eval
                    elif typ == 2: ocore += t2[3]  # other t2 vars define cont in redundant alt_Ps
                    else:          ocore += t2[4]
                    olen += 1
                    t2_x -= 1
            oLen += olen
            oCore += ocore

            fork_.append((_P, _fork_))  # _Ps connected to P, _fork_ for terminated blob transfer to network
            roots += 1  # count of Ps connected to _P, assigned to fork at _P displacement

        if _x > ix:  # or _ix > x:
            buff_.append((_P, _x, _fork_, roots, oLen, oCore))  # for next scan_P_
        else:  # no x overlap between _P and next P: never happens?

            if len(_fork_) == 1 and _fork_[0][1] == 1 and blob_:  # _P'_fork_ == 1 and _fork blob roots == 1 and y > rng *2
                blob = form_blob(_fork_[0], _P, _x)  # y-2 _P is packed in y-3 blob _fork_[0], binding is passed to y-1 P_?
            else:
                blob = (_P, (_x - len(P[9]) / 2), 0, oLen, oCore, [_P])  # blob init, ave_x = _x - len(t2_)/2, Dx = 0
            _P = blob  # binds blob to fork refs in its root Ps?

            if roots == 0:
                net = blob, [(blob, _fork_)]  # net is initialized with terminated blob, no fork_ per net?
                blob = net
                if len(_fork_) == 0:
                    frame = form_frame(typ, net, frame)  # all root-mediated forks terminated, net is packed into frame
                else:
                    _fork_, frame = term_blob(typ, net, _fork_, frame)  # recursive root network termination test
            else:
                blob_.append((blob, roots, _fork_))  # new | continued blobs exposed to P_, with final roots, replace _P_

    buff_ += _buff_  # _buff_ is likely empty
    P_.append((P, x, fork_))  # P with no overlap to next _P is buffered for next-line scan_P_, via y_comp

    return P_, buff_, _P_, blob_, frame  # _P_ and buff_ exclude _Ps displaced into blob_


def term_blob(typ, net, fork_, frame):  # net starts as one terminated blob, then added to terminated forks in its fork_

    for index, (_net, _roots, _fork_) in enumerate(fork_):
        _net = form_network(_net, net)  # terminated network (blob) is included into its forks networks
        fork_[index][0] = _net  # return
        _roots -= 1

        if _roots == 0:
            if len(_fork_) == 0:  # no fork-mediated roots left, terminated net is packed in frame:
                frame = form_frame(typ, net, frame)
            else:
                _fork_, frame = term_blob(typ, _net, _fork_, frame)  # recursive root network termination test

    return fork_, frame  # fork_ contains incremented nets


def form_blob(blob, P, last_x):  # continued or initialized blob is incremented by attached _P, replace by zip?

    (s, L2, I2, D2, Dy2, V2, Vy2, alt_Der, alt_Dir, alt_Both, t2_), _x, Dx, oLen2, oCore2, Py_ = blob
    (s, I, D, Dy, V, Vy, alt_der, alt_dir, alt_both, t2_), oLen, oCore = P  # s is identical, t2_ is a replacement

    x = last_x - len(t2_)/2  # median x, becomes _x in blob, replaces lx
    dx = x - _x  # conditional full comp(x) and comp(S): internal vars are secondary?
    Dx += dx  # for blob normalization and orientation eval, | += |dx| for curved max_L norm, orient?

    L2 += len(t2_)  # t2_ in P buffered in Py_
    I2 += I
    D2 += D; Dy2 += Dy
    V2 += V; Vy2 += Vy
    alt_Der += alt_der
    alt_Dir += alt_dir
    alt_Both+= alt_both
    oLen2 += oLen; oCore2 += oCore  # vertical contiguity between Ps in Py, for blob eval

    Py_.append((s, x, dx, I, D, Dy, V, Vy, alt_der, alt_dir, alt_both, oLen, oCore, t2_))  # dx to normalize P before comp_P?
    blob = (s, L2, I2, D2, Dy2, V2, Vy2, alt_Der, alt_Dir, alt_Both, t2_), _x, Dx, oLen2, oCore2, Py_  # redundant s and t2_

    return blob

def form_network(net, blob):  # continued or initialized network is incremented by attached blob and _root_

    (s, xn, Dxn, Ln, In, Dn, Dyn, Vn, Vyn, alt_Der, alt_Dir, alt_Both, oLenn, oCoren), blob_ = net  # 2D blob_: fork_ per layer?
    ((s, L2, I2, D2, Dy2, V2, Vy2, alt_der, alt_dir, alt_both, t2_), x, Dx, oLen2, oCore2, Py_), fork_ = blob  # s is redundant

    Dxn += Dx  # for net normalization, orient eval, += |Dx| for curved max_L?
    Ln += L2
    In += I2
    Dn += D2; Dyn += Dy2
    Vn += V2; Vyn += Vy2
    alt_Der += alt_der
    alt_Dir += alt_dir
    alt_Both+= alt_both
    oLenn += oLen2; oCoren += oCore2

    blob_.append((x, Dx, L2, I2, D2, Dy2, V2, Vy2, alt_der, alt_dir, alt_both, oLen2, oCore2, Py_, fork_))  # Dx to normalize blob before comp_P
    net = ((s, Ln, In, Dn, Dyn, Vn, Vyn, alt_Der, alt_Dir, alt_Both), xn, Dxn, oLenn, oCoren, Py_), blob_  # separate S_par tuple?

    return net

def form_frame(typ, net, frame):
    ((s, Ln, In, Dn, Dyn, Vn, Vyn, alt_der, alt_dir, alt_both), xn, Dxn, oLenn, oCoren, Py_), blob_ = net

    if typ:
        Dxf, Lf, oLenf, oCoref, net_ = frame  # summed per typ regardless of sign, no typ olp: complete overlap?
    else:
        Dxf, Lf, oLenf, oCoref, net_, If, Df, Dyf, Vf, Vyf, alt_Der, alt_Dir, alt_Both = frame

    Dxf += Dxn  # for frame normalization, orient eval, += |Dxn| for curved max_L?
    Lf += Ln
    oLenf += oLenn; oCoref += oCoren  # for average vertical contiguity, relative to ave Ln?
    net_.append((xn, Dxn, Ln, In, Dn, Dyn, Vn, Vyn, alt_der, alt_dir, alt_both, oLenn, oCoren, blob_))  # Dxn to normalize net before comp_P

    if typ:
        frame = Dxf, Lf, oLenf, oCoref, net_  # no sign, summed cores are already in typ 0
    else:
        If += In  # to compute averages, for dframe only: redundant for same-scope alt_frames?
        Df += Dn; Dyf += Dyn
        Vf += Vn; Vyf += Vyn
        alt_Der += alt_der
        alt_Dir += alt_dir
        alt_Both += alt_both
        frame = Dxf, Lf, oLenf, oCoref, net_, If, Df, Dyf, Vf, Vyf, alt_Der, alt_Dir, alt_Both

    return frame


def image_to_blobs(f):  # postfix '_' distinguishes array vs. element, prefix '_' distinguishes higher-line vs. lower-line variable

    _dP_, _vP_, _dyP_, _vyP_ = deque(),deque(),deque(),deque()  # higher-line same- d-, v-, dy-, vy- sign 1D patterns
    dblob_, vblob_, dyblob_, vyblob_ = deque(),deque(),deque(),deque()  # line y- 3+ rng2: replaces _P_, exposed blobs include _Ps

    dframe = 0,0,0,0,[], 0,0,0,0,0,0,0,0  # Dxf, Lf, oLenf, oCoref, net_, If, Df, Dyf, Vf, Vyf, Daf, Dayf, Vaf, Vayf
    vframe = 0,0,0,0,[]  # Dxf, Lf, oLenf, oCoref, net_; core vars are in dframe
    dyframe = 0,0,0,0,[]
    vyframe = 0,0,0,0,[]  # constituent net rep may select sum | [nets], same for blob?

    global y; y = 0  # vertical coordinate of current input line

    t2_ = deque(maxlen=rng)  # vertical buffer of incomplete quadrant tuples, for fuzzy ycomp
    t2__ = []  # vertical buffer + horizontal line: 2D array of 2D tuples, deque for speed?
    p_ = f[0, :]  # first line of pixels
    t_ = lateral_comp(p_)  # after part_comp (pop, no t_.append) while x < rng?

    for (p, d, m) in t_:
        t2 = p, d, m, 0, 0  # dy, my initialized at 0
        t2_.append(t2)  # only one tuple per first-line t2_
        t2__.append((t2_, 0, 0))  # _dy, _my initialized at 0

    for y in range(1, Y):  # or Y-1: default term_blob in scan_P_ at y = Y?

        p_ = f[y, :]  # vertical coordinate y is index of new line p_
        t_ = lateral_comp(p_)  # lateral pixel comparison
        # vertical pixel comparison:

        t2__, _dP_, _vP_, _dyP_, _vyP_, dblob_, vblob_, dyblob_, vyblob_, dframe, vframe, dyframe, vyframe = \
        vertical_comp(t_, t2__, _dP_, _vP_, _dyP_, _vyP_, dblob_, vblob_, dyblob_, vyblob_, dframe, vframe, dyframe, vyframe)

    # frame ends, last vertical rng of incomplete t2__ is discarded,
    # but vertically incomplete P_ patterns are still inputted in scan_P_?

    return dframe, vframe, dyframe, vyframe  # frame of 2D patterns is outputted to level 2

# pattern filters: eventually updated by higher-level feedback, initialized here as constants:

rng = 2  # number of leftward and upward pixels compared to each input pixel
ave = 127 * rng*2  # average match: value pattern filter
ave_rate = 0.25  # average match rate: ave_match_between_ds / ave_match_between_ps, init at 1/4: I / M (~2) * I / D (~2)

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('-i', '--image', help='path to image file', default='./images/racoon.jpg')
arguments = vars(argument_parser.parse_args())

# read image as 2d-array of pixels (gray scale):
image = cv2.imread(arguments['image'], 0).astype(int)
Y, X = image.shape  # image height and width

start_time = time()
blobs = image_to_blobs(image)
end_time = time() - start_time
print(end_time)
