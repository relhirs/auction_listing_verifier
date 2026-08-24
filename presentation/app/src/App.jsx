import Navbar from './components/layout/Navbar'
import Header from './components/layout/Header'
import SectionWrapper from './components/layout/SectionWrapper'
import Footer from './components/layout/Footer'

import PipelineStepper from './components/pipeline/PipelineStepper'

import AccuracyTrajectory from './components/performance/AccuracyTrajectory'
import PerCheckBreakdown from './components/performance/PerCheckBreakdown'

import McNemarPanel from './components/calibration/McNemarPanel'
import BootstrapCIChart from './components/calibration/BootstrapCIChart'
import BrierCalibrationChart from './components/calibration/BrierCalibrationChart'
import ROCComparisonChart from './components/calibration/ROCComparisonChart'
import LogisticRegressionDrawer from './components/calibration/LogisticRegressionDrawer'

import WeightingSchemeToggle from './components/stress-test/WeightingSchemeToggle'
import ThresholdCurveChart from './components/stress-test/ThresholdCurveChart'
import PhotoSamplingChart from './components/stress-test/PhotoSamplingChart'
import EconomicsTable from './components/economics/EconomicsTable'

import TakeawaysAccordion from './components/insights/TakeawaysAccordion'
import LimitationsPanel from './components/insights/LimitationsPanel'
import FutureWorkPanel from './components/insights/FutureWorkPanel'

export default function App() {
  return (
    <div className="min-h-screen bg-[#F9F9F8]">
      <Navbar />
      <Header />

      <SectionWrapper
        id="system"
        eyebrow="00 The system"
        title="Five stages, two of them never call a model"
      >
        <PipelineStepper />
      </SectionWrapper>

      <SectionWrapper
        id="what-changed"
        eyebrow="01 What changed"
        title="From 77.5% to 87.5%"
        subtitle="Two root cause fixes, both traced back to the same kind of bug."
      >
        <div className="flex flex-col gap-6">
          <AccuracyTrajectory />
          <PerCheckBreakdown />
        </div>
      </SectionWrapper>

      <SectionWrapper
        id="not-luck"
        eyebrow="02 Checking it wasn't luck"
        title="Was the drivetrain fix real?"
        subtitle="A paired significance test on the exact 20 auctions that were affected."
      >
        <div className="flex flex-col gap-6">
          <BootstrapCIChart />
          <McNemarPanel />
        </div>
      </SectionWrapper>

      <SectionWrapper
        id="trust"
        eyebrow="03 How much to trust it"
        title="How trustworthy are the scores?"
        subtitle="A check can catch every real error and still be wrong about how sure it should be."
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <BrierCalibrationChart />
          <ROCComparisonChart />
        </div>
        <LogisticRegressionDrawer />
      </SectionWrapper>

      <SectionWrapper
        id="stress-test"
        eyebrow="04 Stress testing the result"
        title="Does 87.5% hold up under different assumptions?"
        subtitle="Reweight the error mix, move the confidence floor, sample fewer photos, see what breaks."
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <WeightingSchemeToggle />
          <ThresholdCurveChart />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <PhotoSamplingChart />
          <EconomicsTable />
        </div>
      </SectionWrapper>

      <SectionWrapper
        id="bottom-line"
        eyebrow="05 Bottom line"
        title="What this project taught me"
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <TakeawaysAccordion />
          <LimitationsPanel />
        </div>
        <FutureWorkPanel />
      </SectionWrapper>

      <Footer />
    </div>
  )
}
