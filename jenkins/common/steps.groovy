def commonVars = load 'common/variables.groovy'



def setupCondaEnv() {
    sh """
    wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh
    bash miniforge.sh -b -p ${WORKSPACE}/miniforge
    source ${WORKSPACE}/miniforge/bin/activate
    conda env create -f ${commonVars.condaEnvYaml}
    echo "source ${WORKSPACE}/miniforge/bin/activate ${commonVars.condaEnvName}" >> ${WORKSPACE}/activate_conda.sh
    """
}


def createHash() {
    sh """
    source ${WORKSPACE}/activate_conda.sh
    python scripts/hash.py --hash-file ${WORKSPACE}/${commonVars.hashFilename}
    """
}


def createConfig() {
    withCredentials([string(credentialsId: commonVars.githubCredentialsId, variable: 'GITHUB_AUTH_TOKEN')]) {
        sh """
        source ${WORKSPACE}/activate_conda.sh
        python scripts/create_config_file.py --config ${commonVars.configFilename} --auth-token ${GITHUB_AUTH_TOKEN} --issue-id-file ${WORKSPACE}/${commonVars.issueIdFilename} ||
        (python scripts/report.py --config ${commonVars.configFilename} --auth-token ${GITHUB_AUTH_TOKEN} --issue-id-file ${WORKSPACE}/${commonVars.issueIdFilename} --hash-file ${WORKSPACE}/${commonVars.hashFilename} --jenkins-job-name ${JOB_NAME} --invalid &&
        exit 1)
        """
    }
}


def processRequest() {
    sh """
    source ${WORKSPACE}/activate_conda.sh
    export OMP_NUM_THREADS=${commonVars.nThreads}
    export NETCDF_OUTPUT_FILETYPE=${commonVars.netcdfFormat}
    python src/process_request.py --config ${commonVars.configFilename} --workspace ${WORKSPACE} --extpar-raw-data ${commonVars.extparInputDataPath} --logfile ${WORKSPACE}/${commonVars.logFilename}
    """
}


def archiveAndReport(String status, String commitSha = null, String buildUrl = null) {
    withCredentials([string(credentialsId: commonVars.githubCredentialsId, variable: 'GITHUB_AUTH_TOKEN')]) {
        def optionalArgs = ""
        if (commitSha) {
            optionalArgs += " --commit_sha ${commitSha}"
        }
        if (buildUrl) {
            optionalArgs += " --build_url ${buildUrl}"
        }

        sh """
        source ${WORKSPACE}/activate_conda.sh
        python scripts/archive_output.py --config ${commonVars.configFilename} --workspace ${WORKSPACE} --destination ${commonVars.publicDataPath} --logfile ${WORKSPACE}/${commonVars.logFilename} --hash-file ${WORKSPACE}/${commonVars.hashFilename}
        python scripts/report.py --config ${commonVars.configFilename} --auth_token ${GITHUB_AUTH_TOKEN} --jenkins_job_name ${JOB_NAME} --issue_id_file ${WORKSPACE}/${commonVars.issueIdFilename} --hash-file ${WORKSPACE}/${commonVars.hashFilename} ${extraArgs} --${status}
        """
    }
}



// Make all functions accessible when loaded
return this
