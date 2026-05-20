castellatedMesh true;
snap true;
addLayers true;

maxLocalCells 100000;
maxGlobalCells 2000000;
minRefinementCells 0;
maxLoadUnbalance 0.10;
nCellsBetweenLevels 2;

innerCylinderSurfaceRefinementLevel (3 3);

propellerTipSurfaceRefinementLevel (4 4); // y+ targeting variable

outerCylinderRefinementRegionLevel ((1E15 2));
innerCylinderRefinementRegionMode distance;
innerCylinderRefinementRegionLevel ((0.005 3) (0.030 2));

propellerTipRegionLevel 4; //y+ targeting variable


nSmoothPatch 3;
tolerance 1.0;
nSolveIter 30;
nRelaxIter 20;
nFeatureSnapIter 10;
implicitFeatureSnap true;
explicitFeatureSnap true;
multiRegionFeatureSnap true;


relativeSizes false;
propellerTipSurfaceLayers 1;
expansionRatio 1.0;
firstLayerThickness 0.0010067; // y+ targting variable
minThickness 0.0002;
nGrow 0;
featureAngle 180;
addLayersnRelaxIter 5;
nSmoothSurfaceNormals 5; //1
nSmoothNormals 10; //3
nSmoothThickness 30; //20
maxFaceThicknessRatio 5.0; // 2.0
maxThicknessToMedialRatio 2.0; //1.0
minMedialAxisAngle 15; //30
nLayerIter 100; //50
nBufferCellsNoExtrude 0;

maxNonOrtho 65;
maxBoundarySkewness 4;
maxInternalSkewness 4;
maxConcave 80;
minVol 1e-13;
mergeTolerance 1e-6;
nSmoothScale 4;
