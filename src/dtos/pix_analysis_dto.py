from models import PixAnalysis


class PixAnalysisDTO:
    @staticmethod
    def obj_to_dict(pix_analysis: PixAnalysis) -> dict:
        return {
            "key": pix_analysis.analysis_key,
            "status": pix_analysis.status.enumerator,
            "metadata": pix_analysis.analysis_metadata,
        }
