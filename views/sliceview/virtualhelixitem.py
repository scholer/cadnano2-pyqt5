from views import styles
from model.virtualhelix import VirtualHelix
from model.enum import Parity, StrandType
from controllers.itemcontrollers.virtualhelixitemcontroller import VirtualHelixItemController

import util
# import Qt stuff into the module namespace with PySide, PyQt4 independence
util.qtWrapImport('QtCore', globals(), ['Qt', 'QEvent', 'QRectF', 'QPointF'])
util.qtWrapImport('QtGui', globals(), ['QBrush',
                                       'QPen',
                                       'QPainterPath',
                                       'QPolygonF',
                                       'QColor'])
util.qtWrapImport('QtWidgets', globals(), ['QGraphicsEllipseItem',
                                           'QGraphicsItem',
                                           'QGraphicsLineItem',
                                           'QGraphicsSimpleTextItem',
                                           ])


class VirtualHelixItem(QGraphicsEllipseItem):
    """
    The VirtualHelixItem is an individual circle that gets drawn in the SliceView
    as a child of the PartItem. Taken as a group, many SliceHelix
    instances make up the crossection of the DNAPart. Clicking on a SliceHelix
    adds a VirtualHelix to the DNAPart. The SliceHelix then changes appearence
    and paints its corresponding VirtualHelix number.
    """
    # set up default, hover, and active drawing styles
    _useBrush = QBrush(styles.orangefill)
    _usePen = QPen(styles.orangestroke, styles.SLICE_HELIX_STROKE_WIDTH)
    _radius = styles.SLICE_HELIX_RADIUS
    _outOfSlicePen = QPen(styles.lightorangestroke,
                          styles.SLICE_HELIX_STROKE_WIDTH)
    _outOfSliceBrush = QBrush(styles.lightorangefill)
    _rect = QRectF(0, 0, 2 * _radius, 2 * _radius)
    _font = styles.SLICE_NUM_FONT
    _ZVALUE = styles.ZSLICEHELIX+3

    def __init__(self, modelVirtualHelix, emptyHelixItem):
        """
        emptyHelixItem is a EmptyHelixItem that will act as a QGraphicsItem parent
        """
        super(VirtualHelixItem, self).__init__(parent=emptyHelixItem)
        self._virtualHelix = modelVirtualHelix
        self._emptyHelixItem = emptyHelixItem
        self.hide()
        # drawing related

        self.isHovered = False
        self.setAcceptHoverEvents(True)
        # self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(self._ZVALUE)
        self.lastMousePressAddedBases = False

        self.setBrush(self._outOfSliceBrush)
        self.setPen(self._outOfSlicePen)
        self.setRect(self._rect)

        # handle the label specific stuff
        self._label = self.createLabel()
        self.setNumber()
        self.arrows = list()
        self.createArrow()

        self._controller = VirtualHelixItemController(self, modelVirtualHelix)

        self.show()
    # end def

    ### SIGNALS ###

    ### SLOTS ###
    def virtualHelixNumberChangedSlot(self, virtualHelix):
        """
        receives a signal containing a virtualHelix and the oldNumber 
        as a safety check
        """
        self.setNumber()
    # end def

    def virtualHelixRemovedSlot(self, virtualHelix):
        self._controller.disconnectSignals()
        self._controller = None
        self._emptyHelixItem.setNotHovered()
        self._virtualHelix = None
        self._emptyHelixItem = None
        self.scene().removeItem(self._label)
        self._label = None
        self.scene().removeItem(self)
    # end def

    def strandAddedSlot(self, sender, strand):
        pass
    # end def

    ###

    def createLabel(self):
        """ Adds a label with the helix number in the center of the helix item. """
        label = QGraphicsSimpleTextItem("%d" % self._virtualHelix.number())
        label.setFont(self._font)
        label.setZValue(self._ZVALUE+10)
        label.setParentItem(self)
        return label
    # end def

    def genericArrow(self, color=None, alpha=None, width=2, rad=None, zvalue=3, hidden=True, rotation=0):
        """
        Creates a generic arrow/marker/hand to indicate backbone twist location.
        """
        rad = rad or self._radius
        pen = QPen()
        pen.setWidth(width)
        color = QColor(color or Qt.blue)
        color.setAlphaF(alpha or 0.25)
        pen.setBrush(color)
        # If we create the arrow depending on even/odd parity, then we can use the
        # same code for updatearrow for arrows on all helices.
        # (However, it does feel like a hack...)
        if self._virtualHelix.isEvenParity():
            # If line width is 3, then the arrow marker looks better if it only has length of 0.9*rad.
            arrow = QGraphicsLineItem(rad*1.1, rad, 0.95*2*rad, rad, self)
        else:
            # was: 0, rad, rad, rad
            arrow = QGraphicsLineItem(0.1*rad, rad, 0.9*rad, rad, self)
        arrow.setTransformOriginPoint(rad, rad)
        arrow.setZValue(self._ZVALUE+zvalue)
        arrow.setPen(pen)
        if hidden:
            arrow.hide()
        if rotation:
            arrow.setRotation(rotation)
        return arrow


    def createArrow(self):
        """
        Creates a marker/arrow/hand to indicate backbone twist location.
        Update: Adjusted scaffold marker and added marker for staple strand backbone.
        Question: What part of the nucleotide should be used for the marker?
        * The 5' phosphate? No, that is not really representative of the nucleotide.
        * The ribose C5'?
        * The ribose (average/center)? Or the ribose C1'?
        * The ribose C3'? Yes, this is actually a pretty good point.
        The "angle" of the minor groove depends a lot on this.
        Structurally, it is probably the C5' which is the most relevant,
        since the 5' phosphate should be completely flexible.
        However, when making a normal 'holliday' crossover between anti-parallel strands
        and you want to see which bases are opposite, then you have connection between
        C5' to C3' (not C5' to C5'). This would argue for using the ribose center.
        For consistency, I guess you could add both?
        Note that the phosphate between C3 and C5 accounts for as much angular rotation as the ribose.
        A further note: The minor/major groove will, of cause, depend on how you look at the
        helix. In cadnano, the slice view is viewed from left to right relative
        to the path view. This means that helices with even parity looks different in the
        sliceview than helices with odd parity.
        """
        # For even parity, scafC5 is above scafC3, and vice versa for stap.
        # For even parity, it should be: scafC5 > scafC3 = stapC3 > stapC5.
        direction = 1 if self._virtualHelix.isEvenParity() else -1
        arrowspecs = [#dict(color=Qt.black, alpha=0.5, width=0.5, rad=self._radius, zvalue=0),      # marker
                      dict(color=Qt.blue, alpha=0.8, width=3, rad=self._radius, zvalue=direction*4),       # scafC3
                      dict(color=Qt.darkGray, alpha=0.8, width=3, rad=self._radius, zvalue=direction*6),   # scafC5
                      dict(color=Qt.red, alpha=0.8, width=3, rad=self._radius, zvalue=direction*4, rotation=190),  # stapC3
                      dict(color=Qt.darkGray, alpha=0.8, width=3, rad=self._radius, zvalue=direction*2, rotation=175), # stapC5
                      ]
        arrowattrnames = ['arrow_scafC3', 'arrow_scafC5', 'arrow_stapC3', 'arrow_stapC5']
        for arrowname, arrowspec in zip(arrowattrnames, arrowspecs):
            arrow = self.genericArrow(**arrowspec)
            self.arrows.append(arrow)
            setattr(self, arrowname, arrow)
        # How much each arrow should be offset compared to the "global" virtualhelix angle at bp index:
        # Global angle seems to be: "scaffold, if scaffold were opposite staple". Yes.
        # For even parity stapC5' is more CW than stapC3'
        # For a part._twistOffset = -12, (190, 175) seems good for stapC3/C5.
        self.arrow_angle_offsets = [-40, -25, 190, 175]  # [scafC3, scafC5, stapC3, stapC5]
        # angle C3-C3 is 180-10-40=130 degrees, C5-C5 is 180+5-25=160, average is 145.
        # (used to be 125, 155 and 140 avg, but that seems a bit much...)
    # end def

    def updateArrow(self, idx):
        """
        Update: Adjusted scaffold marker and added marker for staple strand backbone.
        Note that currently, I have also adjusted part._twistOffset to make it right.
        Not sure if this is the right way to tweak it?
        """
        part = self.part()
        tpb = part._twistPerBase # degrees
        angle = idx*tpb
        isevenparity = self._virtualHelix.isEvenParity()
        # the overall rotation of a helix is usually specified by the staple strand
        # (which usually makes the majority of crossovers)
        # The angle between the phosphate of a base pair between antiparallel strands is
        # approx 140 degrees (minor groove). It might be less, but let's assume 140 for now.
        # The "overall cadnano basepair angle" seems to be specified by
        # "where the scaffold backbone would be, if it was right opposite (180 degree) from the staple strand."
        direction = 1 if isevenparity else -1
        for arrow, arrow_offset in zip(self.arrows, self.arrow_angle_offsets):
            arrow.setRotation(angle + part._twistOffset - arrow_offset*direction)
        # end def

    def setNumber(self):
        """docstring for setNumber"""
        vh = self._virtualHelix
        num = vh.number()
        label = self._label
        radius = self._radius

        if num != None:
            label.setText("%d" % num)
        else:
            return

        y_val = radius / 3
        if num < 10:
            label.setPos(radius / 1.5, y_val)
        elif num < 100:
            label.setPos(radius / 3, y_val)
        else: # _number >= 100
            label.setPos(0, y_val)
        bRect = label.boundingRect()
        posx = bRect.width()/2
        posy = bRect.height()/2
        label.setPos(radius-posx, radius-posy)
    # end def

    def part(self):
        return self._emptyHelixItem.part()

    def virtualHelix(self):
        return self._virtualHelix
    # end def

    def number(self):
        return self.virtualHelix().number()

    def setActiveSliceView(self, isActiveNow, idx):
        if isActiveNow:
            self.setPen(self._usePen)
            self.setBrush(self._useBrush)
            self.updateArrow(idx)
            for arrow in self.arrows:
                arrow.show()
        else:
            self.setPen(self._outOfSlicePen)
            self.setBrush(self._outOfSliceBrush)
            for arrow in self.arrows:
                arrow.hide()
    # end def

    ############################ User Interaction ############################
    def sceneEvent(self, event):
        """Included for unit testing in order to grab events that are sent
        via QGraphicsScene.sendEvent()."""
        # if self._parent.sliceController.testRecorder:
        #     coord = (self._row, self._col)
        #     self._parent.sliceController.testRecorder.sliceSceneEvent(event, coord)
        if event.type() == QEvent.MouseButtonPress:
            self.mousePressEvent(event)
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(event)
            return True
        elif event.type() == QEvent.MouseMove:
            self.mouseMoveEvent(event)
            return True
        QGraphicsItem.sceneEvent(self, event)
        return False

    def hoverEnterEvent(self, event):
        """
        If the selection is configured to always select
        everything, we don't draw a focus ring around everything,
        instead we only draw a focus ring around the hovered obj.
        """
        # if self.selectAllBehavior():
        #     self.setSelected(True)
        # forward the event to the emptyHelixItem as well
        self._emptyHelixItem.hoverEnterEvent(event)
    # end def

    def hoverLeaveEvent(self, event):
        # if self.selectAllBehavior():
        #     self.setSelected(False)
        self._emptyHelixItem.hoverEnterEvent(event)
    # end def

    # def mousePressEvent(self, event):
    #     action = self.decideAction(event.modifiers())
    #     action(self)
    #     self.dragSessionAction = action
    # 
    # def mouseMoveEvent(self, event):
    #     parent = self._helixItem
    #     posInParent = parent.mapFromItem(self, QPointF(event.pos()))
    #     # Qt doesn't have any way to ask for graphicsitem(s) at a
    #     # particular position but it *can* do intersections, so we
    #     # just use those instead
    #     parent.probe.setPos(posInParent)
    #     for ci in parent.probe.collidingItems():
    #         if isinstance(ci, SliceHelix):
    #             self.dragSessionAction(ci)
    # # end def

    # def mouseReleaseEvent(self, event):
    #     self.part().needsFittingToView.emit()

    # def decideAction(self, modifiers):
    #     """ On mouse press, an action (add scaffold at the active slice, add
    #     segment at the active slice, or create virtualhelix if missing) is
    #     decided upon and will be applied to all other slices happened across by
    #     mouseMoveEvent. The action is returned from this method in the form of a
    #     callable function."""
    #     vh = self.virtualHelix()
    #     if vh == None: return SliceHelix.addVHIfMissing
    #     idx = self.part().activeSlice()
    #     if modifiers & Qt.ShiftModifier:
    #         if vh.stap().get(idx) == None:
    #             return SliceHelix.addStapAtActiveSliceIfMissing
    #         else:
    #             return SliceHelix.nop
    #     if vh.scaf().get(idx) == None:
    #         return SliceHelix.addScafAtActiveSliceIfMissing
    #     return SliceHelix.nop
    # 
    # def nop(self):
    #     pass
